import inject
from book_cruises.commons.utils import MessageMiddleware, Database, logger
from book_cruises.commons.domains import Itinerary, ItineraryDTO
from book_cruises.commons.domains.repositories import ItineraryRepository
from .di import initialize_dependencies

class BookSvc:
    @inject.autoparams()
    def __init__(self, msg_middleware: MessageMiddleware, database: Database):
        self.__msg_middleware: MessageMiddleware = msg_middleware
        self.__repository = ItineraryRepository(database)
    
    def __process_itinerary(self, itinerary_data: str) -> None:
        try:
            itinerary_dto = ItineraryDTO.parse_raw(itinerary_data)
            logger.info(f"Received itinerary query: {itinerary_dto}")

            itineraries = self.__repository.get_itineraries(itinerary_dto)
            print(f"Available itineraries: {itineraries}")
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
    
    def run(self):
        logger.info("Book Service initialized")
        self.__msg_middleware.consume_messages(self.__process_itinerary)

def main() -> None: 
    initialize_dependencies()

    book_svc = BookSvc()
    book_svc.run()




