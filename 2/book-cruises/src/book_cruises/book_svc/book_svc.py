import inject
import json
from book_cruises.commons.utils import config
from book_cruises.commons.utils import Consumer, Database, logger
from book_cruises.commons.domains import Itinerary, ItineraryDTO
from book_cruises.commons.domains.repositories import ItineraryRepository
from .di import initialize_dependencies


class BookSvc:
    @inject.autoparams()
    def __init__(self, consumer: Consumer, database: Database):
        self.__consumer: Consumer = consumer
        self.__repository = ItineraryRepository(database)

    def __process_itinerary(self, itinerary_data: str) -> None:
    
        try:
            itinerary_dto = ItineraryDTO.parse_raw(itinerary_data)

            itineraries = self.__repository.get_itineraries(itinerary_dto)
            logger.debug(f"Available itineraries: {itineraries}")

            list_itineraries_dict = []
            for itinerary in itineraries:
                itinerary_json = itinerary.json()
                list_itineraries_dict.append(json.loads(itinerary_json))

            # Convert the list of itineraries to JSON
            json_encoded_itineraries = json.dumps(list_itineraries_dict)
            return json_encoded_itineraries

        except Exception as e:
            logger.error(f"Failed to process message: {e}")

    def run(self):
        logger.info("Book Service initialized")
        self.__consumer.declare_queue(
            config.BOOK_SVC_QUEUE, durable=False
        )
        self.__consumer.register_callback(config.BOOK_SVC_QUEUE, self.__process_itinerary)
        self.__consumer.start_consuming()


def main() -> None:
    initialize_dependencies()

    book_svc = BookSvc()
    book_svc.run()
