import inject
import json
from book_cruises.commons.utils import config, logger, cryptographer
from book_cruises.commons.messaging import Consumer
from book_cruises.commons.database import Database
from book_cruises.commons.domains import ItineraryDTO
from book_cruises.commons.domains.repositories import ItineraryRepository
from .di import configure_dependencies  


class BookSvc:
    @inject.autoparams()
    def __init__(self, consumer: Consumer, database: Database):
        self.__PAYMENT_PUBLIC_KEY_PATH = "src/book_cruises/book_svc/public_keys/payment_svc_public_key.pem"
        self.__payment_public_key = cryptographer.load_public_key(self.__PAYMENT_PUBLIC_KEY_PATH)

        self.__consumer: Consumer = consumer
        self.__repository = ItineraryRepository(database)

    def __query_itinerary(self, itinerary_data: dict) -> list:

        try:
            itinerary_dto = ItineraryDTO(**itinerary_data)

            itineraries = self.__repository.get_itineraries(itinerary_dto)
            logger.debug(f"Available itineraries: {itineraries}")

            list_itineraries_dict = []
            for itinerary in itineraries:
                itinerary_json = itinerary.json()
                list_itineraries_dict.append(json.loads(itinerary_json))

            return list_itineraries_dict

        except Exception as e:
            logger.error(f"Failed to process message: {e}")
        
    def __process_payment(self, payment_data: dict) -> None:
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
    
        if status == "refused":
            logger.error(f"Processing refused payment with data: {message}")
        elif status == "approved":
            logger.info(f"Processing approved payment with data: {message}")
    
    def run(self):
        logger.info("Book Service initialized")
        self.__consumer.declare_queue(config.QUERY_RESERVATION_QUEUE, durable=False)
        self.__consumer.declare_queue(config.RESERVE_CREATED_QUEUE, durable=False)

        self.__consumer.register_callback(config.QUERY_RESERVATION_QUEUE, self.__query_itinerary)
        self.__consumer.register_callback(config.REFUSED_PAYMENT_QUEUE, self.__process_payment)
        self.__consumer.register_callback(config.APPROVED_PAYMENT_QUEUE, self.__process_payment)

        self.__consumer.start_consuming()


def main() -> None:
    configure_dependencies()

    book_svc = BookSvc()
    book_svc.run()
