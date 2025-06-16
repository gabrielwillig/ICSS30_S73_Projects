import requests
import inject
from flask import Flask, request, jsonify

from book_cruises.commons.domains import Reservation, Payment
from book_cruises.commons.utils import config, logger
from book_cruises.commons.messaging import Producer
from .di import configure_dependencies


class PaymentSvc:
    @inject.autoparams()
    def __init__(self, producer: Producer):
        self.__producer: Producer = producer

    def generate_payment_link(self, reservation: Reservation) -> dict:
        payment = Payment.create_payment(
            total_price=reservation.total_price,
            reservation_id=reservation.id,
            itinerary_id=reservation.itinerary_id,
            client_id=reservation.client_id,
        )

        response = requests.post(
            f"http://{config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_HOST}:{config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_PORT}/external/receives-payment",
            json=payment.model_dump(),
            timeout=config.REQUEST_TIMEOUT,
        )

        reservation_info = {
            "reservation_id": reservation.id,
            "payment_link": f"http://{config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_HOST}:{config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_PORT}/payment_link?reservation_id={reservation.id}&client_id={reservation.client_id}",
        }

        reservation_info.update(response.json())
        return reservation_info

    def handle_payment_status(self, payment: Payment) -> tuple[dict, int]:
        match payment.status:
            case Payment.APPROVED:
                logger.info("payment approved")
                self.__producer.publish(
                    config.APPROVED_PAYMENT_ROUTING_KEY,
                    payment.model_dump(),
                    config.APP_EXCHANGE,
                )
            case Payment.REFUSED:
                logger.warning("payment refused")
                self.__producer.publish(
                    config.REFUSED_PAYMENT_QUEUE, payment.model_dump()
                )
            case _:
                return {"error": "unknown status"}, 400

        logger.debug(f"Payment status '{payment.status}' published to queue")

        return {"message": "status processed"}, 200


def create_flask_app(payment_svc: PaymentSvc) -> Flask:
    app = Flask(__name__)

    @app.route("/payment/link", methods=["POST"])
    def generate_link():
        reservation = Reservation(**request.json)
        response = payment_svc.generate_payment_link(reservation)
        return jsonify(response), 201

    @app.route("/payment/notify", methods=["POST"])
    def update_payment_status():
        payment: Payment = Payment(**request.json)
        response, code = payment_svc.handle_payment_status(payment)
        return jsonify(response), code

    return app


def main() -> None:
    configure_dependencies()

    payment_svc = PaymentSvc()

    app = create_flask_app(payment_svc)

    logger.info(
        f"Starting Payment Service on 'http://{config.PAYMENT_SVC_WEB_SERVER_HOST}:{config.PAYMENT_SVC_WEB_SERVER_PORT}'"
    )

    app.run(
        host=config.PAYMENT_SVC_WEB_SERVER_HOST,
        port=config.PAYMENT_SVC_WEB_SERVER_PORT,
        debug=config.DEBUG,
    )
