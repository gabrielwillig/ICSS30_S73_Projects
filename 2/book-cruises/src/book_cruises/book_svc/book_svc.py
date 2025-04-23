import inject
import json
from book_cruises.commons.utils import config, logger
from book_cruises.commons.messaging import Consumer
from book_cruises.commons.database import Database
from book_cruises.commons.domains import ItineraryDTO
from book_cruises.commons.domains.repositories import ItineraryRepository
from .di import configure_dependencies  


class BookSvc:
    @inject.autoparams()
    def __init__(self, consumer: Consumer, database: Database):
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


    def run(self):
        logger.info("Book Service initialized")
        self.__consumer.declare_queue(config.QUERY_RESERVATION_QUEUE, durable=False)
        self.__consumer.register_callback(config.QUERY_RESERVATION_QUEUE, self.__query_itinerary)

        self.__consumer.declare_queue(config.RESERVE_CREATED_QUEUE, durable=False)
        self.__consumer.start_consuming()


def main() -> None:
    configure_dependencies()

    book_svc = BookSvc()
    book_svc.run()
