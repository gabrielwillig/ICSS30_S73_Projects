import inject
import uuid
from book_cruises.commons.utils import config, logger, cryptographer
from book_cruises.commons.messaging import Consumer, Producer
from .di import configure_dependencies


class TicketSvc:
    @inject.autoparams()
    def __init__(self, consumer: Consumer, producer: Producer):
        self.__PAYMENT_PUBLIC_KEY_PATH = "src/book_cruises/ticket_svc/public_keys/payment_svc_public_key.pem"
        self.__payment_public_key = cryptographer.load_public_key(self.__PAYMENT_PUBLIC_KEY_PATH)

        self.__consumer: Consumer = consumer
        self.__producer: Producer = producer

    def __process_ticket(self, payment_data: dict) -> None:
        signature_is_valid = cryptographer.verify_signature(
            payment_data["message"],
            payment_data["signature"],
            self.__payment_public_key,
        )
        if not signature_is_valid:
            logger.error("Invalid signature")
            raise NotImplementedError("Invalid signature")

        message = payment_data["message"]
        status = message["status"]
    
        if status != "approved":
            logger.error(f"Error processing ticket with data: {message}")
            return
        
        logger.info(f"Processing approved ticket with data: {message}")
        ticket_data = {
            "ticket_id": str(uuid.uuid4()),
            "message": message
        }
        self.__producer.publish(
            config.TICKET_GENERATED_QUEUE,
            ticket_data,
        )
        logger.info(f"Ticket generated with data: {ticket_data}")


    def run(self):
        logger.info("Ticket Service Initialized")
        self.__consumer.declare_queue(config.TICKET_GENERATED_QUEUE, durable=False)

        self.__consumer.register_callback(config.APPROVED_PAYMENT_QUEUE, self.__process_ticket)
        self.__consumer.start_consuming()


def main() -> None:
    configure_dependencies()

    ticket_svc = TicketSvc()
    ticket_svc.run()
