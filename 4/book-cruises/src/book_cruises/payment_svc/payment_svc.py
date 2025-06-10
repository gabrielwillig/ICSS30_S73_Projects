import random
from threading import Thread
import time

import inject
from flask import Flask, request, jsonify

from book_cruises.commons.domains import Reservation
from book_cruises.commons.utils import config, logger, cryptographer
from book_cruises.commons.messaging import Consumer, Producer
from .di import configure_dependencies


class PaymentSvc:
    @inject.autoparams()
    def __init__(self, consumer: Consumer, producer: Producer):
        self.__PAYMENT_PRIVATE_KEY_PATH = (
            "src/book_cruises/payment_svc/private_keys/payment_svc_private_key.pem"
        )
        self.__private_key = cryptographer.load_private_key(
            self.__PAYMENT_PRIVATE_KEY_PATH
        )

        self.__consumer: Consumer = consumer
        self.__producer: Producer = producer

        self.__thread_consumer = None

    def run(self):
        logger.info("Payment Service initialized")

        self.__start_consumer_thread()

    def __start_consumer_thread(self) -> None:
        self.__thread_consumer = Thread(target=self.__target_consumer_thread)
        self.__thread_consumer.start()

    def __target_consumer_thread(self) -> None:
        self.__consumer.register_callback(
            config.RESERVE_CREATED_QUEUE, self.__process_payment
        )
        while True:
            try:
                self.__consumer.start_consuming()
            except Exception as e:
                logger.error(f"Error in thread_consumer: {e.with_traceback()}")
                time.sleep(5)

    def __process_payment(self, payment_data: dict) -> None:
        logger.info(f"Processing payment with data: {payment_data}")

        percentage = random.randint(0, 100)
        # Simulate random success or failure
        if percentage > 40:  # Randomly choose True (success) or False (failure)
            logger.info("Payment approved")

            message = {"status": "approved", "payment_data": payment_data}
            signature = cryptographer.sign_message(message, self.__private_key)
            mensage_signed = {
                "message": message,
                "signature": signature,
            }

            self.__producer.publish(
                routing_key=config.APPROVED_PAYMENT_ROUTING_KEY,
                message=mensage_signed,
                exchange=config.APP_EXCHANGE,
            )
        else:
            logger.error("Payment refused")

            message = {"status": "refused", "payment_data": payment_data}
            signature = cryptographer.sign_message(message, self.__private_key)
            mensage_signed = {
                "message": message,
                "signature": signature,
            }

            self.__producer.publish(
                config.REFUSED_PAYMENT_QUEUE,
                mensage_signed,
            )


def create_flask_app(payment_svc: PaymentSvc) -> Flask:
    app = Flask(__name__)

    @app.route("/generate-link", methods=["POST"])
    def generate_link():
        reservation: Reservation = Reservation(**request.json)

        # Generate a unique payment link (for simplicity, we use a random UUID)
        payment_link = f"http://{config.PAYMENT_SVC_WEB_SERVER_HOST}:{config.PAYMENT_SVC_WEB_SERVER_PORT}/pay/{reservation.id}"

        return jsonify({"payment_link": payment_link}), 200

    return app


def main() -> None:
    configure_dependencies()

    payment_svc = PaymentSvc()
    payment_svc.run()

    app = create_flask_app(payment_svc)
    app.run(
        host=config.PAYMENT_SVC_WEB_SERVER_HOST,
        port=config.PAYMENT_SVC_WEB_SERVER_PORT,
        debug=config.DEBUG,
    )
