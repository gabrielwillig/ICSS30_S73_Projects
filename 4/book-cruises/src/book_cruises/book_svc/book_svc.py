import json
from threading import Thread
import time
import requests

import inject
from flask import Flask, request, jsonify

from book_cruises.commons.utils import config, logger, cryptographer
from book_cruises.commons.messaging import Consumer, Producer
from book_cruises.commons.domains import ItineraryDTO, Reservation, ReservationDTO, Payment
from book_cruises.commons.domains.repositories import ItineraryRepository, ReservationRepository
from .di import configure_dependencies


class BookSvc:

    @inject.autoparams()
    def __init__(self, consumer: Consumer, producer: Producer):

        self.__consumer: Consumer = consumer
        self.__producer: Producer = producer
        self.__itinerary_repository = ItineraryRepository()
        self.__reservation_repository = ReservationRepository()

        self.__reservation_statuses = {}

        self.__first_time = True
        self.__thread_consumer = None

    def run(self):
        logger.info("Book Service initialized")
        self.__config_broker()

        self.__consumer.register_callback(
            config.REFUSED_PAYMENT_QUEUE, self.__process_payment
        )
        self.__consumer.register_callback(
            config.APPROVED_PAYMENT_BOOK_SVC_QUEUE, self.__process_payment
        )
        self.__consumer.register_callback(
            config.TICKET_GENERATED_QUEUE, self.__process_ticket
        )
        logger.info(f"Instance id {id(self)}")

        self.__start_consumer_thread()

    def create_reservation(self, reservation_dto: ReservationDTO):
        reservation: Reservation = self.__reservation_repository.create_reservation(reservation_dto)

        # Store the reservation status
        self.__add_new_reservation(reservation.id)

        # Publish the reservation data to the RESERVE_CREATED_QUEUE
        self.__producer.publish(config.RESERVE_CREATED_QUEUE, reservation.model_dump())
        if self.__first_time:
            self.__producer.publish(config.RESERVE_CREATED_QUEUE, reservation.model_dump())
            self.__first_time = False

        logger.debug(
            f"Published reservation {reservation.model_dump()} to {config.RESERVE_CREATED_QUEUE}"
        )

        # Solicita link de pagamento ao MS Pagamento
        payment_res = requests.post(
            f"http://{config.PAYMENT_SVC_WEB_SERVER_HOST}:{config.PAYMENT_SVC_WEB_SERVER_PORT}/payment/link",
            json=reservation.model_dump(),
            timeout=config.REQUEST_TIMEOUT,
        )

        logger.debug(f"Payment service response: {payment_res.status_code} - {payment_res.text}")

    def get_payment_status(self, reservation_id):
        # Wait for a response from the queues
        try:
            if not reservation_id in self.__reservation_statuses:
                return {"status": "error", "message": "Reservation ID not found"}

            logger.debug(f"Payment status: {self.__reservation_statuses}")
            payment_status = self.__reservation_statuses[reservation_id]["payment"]
            match payment_status:
                case "approved":
                    return {"status": "approved", "message": "Reservation approved"}
                case "refused":
                    return {"status": "refused", "message": "Reservation refused"}
                case "waiting":
                    return {"status": "waiting", "message": "Waiting for payment"}
                case _:
                    return {"status": "error", "message": "Unknown status"}
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return {"status": "error", "message": str(e)}

    def get_ticket_status(self, reservation_id):
        # Wait for a response from the queues
        try:
            if not reservation_id in self.__reservation_statuses:
                return {"status": "error", "message": "Reservation ID not found"}

            logger.debug(f"Ticket status: {self.__reservation_statuses}")
            ticket_status = self.__reservation_statuses[reservation_id]["ticket"]
            match ticket_status:
                case "ticket_generated":
                    return {"status": "ticket_generated", "message": "Ticket generated"}
                case "waiting":
                    return {"status": "waiting", "message": "Waiting for ticket"}
                case _:
                    return {"status": "error", "message": "Unknown status"}
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return {"status": "error", "message": str(e)}

    def __add_new_reservation(self, reservation: Reservation) -> None:
        self.__reservation_statuses[reservation.id] = {
            "payment": "waiting",
            "ticket": "waiting",
        }
        logger.info(f"Added new reservation: {reservation.id}")

    def __update_reservation_payment_status(
        self, payment: Payment
    ) -> None:
        logger.debug(f"__reservation_statuses: {self.__reservation_statuses}")
        self.__reservation_statuses[payment.reservation_id]["payment"] = payment.status
        logger.info(f"Update reservation status: {payment.reservation_id} -> {payment.status}")

    def __update_reservation_ticket_status(
        self, reservation_id: str, status: str
    ) -> None:
        self.__reservation_statuses[reservation_id]["ticket"] = status
        logger.info(f"Update reservation status: {reservation_id} -> {status}")

    def __process_ticket(self, payment_data: dict) -> None:
        self.__update_reservation_ticket_status(
            payment_data["message"]["payment_data"]["reservation_id"],
            "ticket_generated",
        )

    def __process_payment(self, payment_data: dict) -> None:
        payment: Payment = Payment(**payment_data)

        match payment.status:
            case "approved":
                self.__update_reservation_payment_status(
                    payment
                )
            case "refused":
                self.__update_reservation_payment_status(
                    payment
                )
            case _:
                logger.error(f"Unknown status: {payment.status}")

    def __target_consumer_thread(self) -> None:
        while True:
            try:
                self.__consumer.start_consuming()
            except Exception as e:
                logger.error(f"Error in thread_consumer: {e.with_traceback()}")
                time.sleep(5)

    def __start_consumer_thread(self) -> None:
        self.__thread_consumer = Thread(target=self.__target_consumer_thread)
        self.__thread_consumer.start()

    def __config_broker(self) -> None:
        self.__consumer.exchange_declare(config.APP_EXCHANGE, "direct", durable=False)

        self.__consumer.queue_declare(config.RESERVE_CREATED_QUEUE, durable=False)
        self.__consumer.queue_declare(
            config.APPROVED_PAYMENT_TICKET_QUEUE, durable=False
        )
        self.__consumer.queue_declare(
            config.APPROVED_PAYMENT_BOOK_SVC_QUEUE, durable=False
        )
        self.__consumer.queue_declare(config.REFUSED_PAYMENT_QUEUE, durable=False)
        self.__consumer.queue_declare(config.TICKET_GENERATED_QUEUE, durable=False)

        self.__consumer.queue_bind(
            queue_name=config.APPROVED_PAYMENT_BOOK_SVC_QUEUE,
            exchange=config.APP_EXCHANGE,
            routing_key=config.APPROVED_PAYMENT_ROUTING_KEY,
        )
        self.__consumer.queue_bind(
            queue_name=config.APPROVED_PAYMENT_TICKET_QUEUE,
            exchange=config.APP_EXCHANGE,
            routing_key=config.APPROVED_PAYMENT_ROUTING_KEY,
        )


def create_flask_app(book_svc: BookSvc) -> Flask:
    app = Flask(__name__)

    @app.route("/book/get-itineraries", methods=["POST"])
    def get_itineraries():
        itinerary_data = request.json
        response = requests.post(config.ITINERARY_SVC_URL + "/itinerary/get-itineraries", json=itinerary_data, timeout=config.REQUEST_TIMEOUT)

        return jsonify(response.json()), response.status_code

    @app.route("/create_reservation", methods=["POST"])
    def create_reservation():
        reservation_dto = ReservationDTO(
            client_id=0,
            number_of_guests=request.json["passengers"],
            itinerary_id=request.json["trip_id"],
            total_price=request.json["price"],
        )
        result = book_svc.create_reservation(reservation_dto)
        return jsonify(result), 200

    @app.route("/payment/status", methods=["GET"])
    def get_payment_status():
        reservation_id = request.args.get("reservation_id")
        result = book_svc.get_payment_status(reservation_id)
        if (
            result.get("status") == "error"
            and result.get("message") == "Reservation ID not found"
        ):
            return jsonify(result), 404
        return jsonify(result), 200

    @app.route("/ticket/status", methods=["GET"])
    def get_ticket_status():
        reservation_id = request.args.get("reservation_id")
        result = book_svc.get_ticket_status(reservation_id)
        if (
            result.get("status") == "error"
            and result.get("message") == "Reservation ID not found"
        ):
            return jsonify(result), 404
        return jsonify(result), 200

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok"}), 200

    return app


def main() -> None:
    configure_dependencies()

    book_svc = BookSvc()
    book_svc.run()

    # Create and run the Flask app
    app = create_flask_app(book_svc)
    app.run(
        port=config.BOOK_SVC_WEB_SERVER_PORT,
        host=config.BOOK_SVC_WEB_SERVER_HOST,
        debug=config.DEBUG,
    )
