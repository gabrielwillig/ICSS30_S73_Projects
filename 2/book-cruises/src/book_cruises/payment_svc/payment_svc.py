import inject
import random
from book_cruises.commons.utils import config, logger, cryptographer
from book_cruises.commons.messaging import Consumer, Producer
from .di import configure_dependencies


class PaymentSvc:
    @inject.autoparams()
    def __init__(self, consumer: Consumer, producer: Producer):
        self.__PAYMENT_PRIVATE_KEY_PATH = "src/book_cruises/payment_svc/private_keys/payment_svc_private_key.pem"
        self.__private_key = cryptographer.load_private_key(self.__PAYMENT_PRIVATE_KEY_PATH)

        self.__consumer: Consumer = consumer
        self.__producer: Producer = producer

    def __process_payment(self, payment_data: dict) -> None:
        logger.info(f"Processing payment with data: {payment_data}")

        percentage = random.randint(0, 100)
        # Simulate random success or failure
        if percentage > 30:  # Randomly choose True (success) or False (failure)
            logger.info("Payment approved")

            message = {"status": "approved", "payment_data": payment_data}
            signature = cryptographer.sign_message(message, self.__private_key)
            mensage_signed = {
                "message": message,
                "signature": signature,
            }

            self.__producer.publish(
                config.APPROVED_PAYMENT_QUEUE,
                mensage_signed,
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

    def run(self):
        logger.info("Payment Service initialized")
        self.__consumer.declare_queue(config.APPROVED_PAYMENT_QUEUE, durable=False)
        self.__consumer.declare_queue(config.REFUSED_PAYMENT_QUEUE, durable=False)

        self.__consumer.register_callback(config.RESERVE_CREATED_QUEUE, self.__process_payment)
        self.__consumer.start_consuming()


def main() -> None:
    configure_dependencies()

    payment_svc = PaymentSvc()
    payment_svc.run()
