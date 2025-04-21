import inject
import uuid
from book_cruises.commons.utils import config
from book_cruises.commons.utils import MessageMiddleware, Database, logger
from book_cruises.commons.domains import Itinerary, ItineraryDTO
from book_cruises.commons.domains.repositories import ItineraryRepository
from .di import initialize_dependencies

class BookSvc:
    @inject.autoparams()
    def __init__(self, msg_middleware: MessageMiddleware, database: Database):
        self.__msg_middleware: MessageMiddleware = msg_middleware
        self.__repository = ItineraryRepository(database)
        self.__response_storage = {}  # Temporary storage for tracking responses

        self.__queue_callbacks = {
            config.BOOK_SVC_QUEUE: self.__process_itinerary,
        }
    
    def __process_itinerary(self, itinerary_data: str, properties: dict) -> None:
        response_queue = properties.reply_to
        logger.debug(f"Reply to queue: {response_queue}")
        correlation_id = properties.correlation_id
        logger.debug(f"Received itinerary query with correlation_id {correlation_id}: {itinerary_data}")
        try:
            itinerary_dto = ItineraryDTO.parse_raw(itinerary_data)
            logger.debug(f"Received itinerary query: {itinerary_dto}")

            itineraries = self.__repository.get_itineraries(itinerary_dto)
            logger.debug(f"Available itineraries: {itineraries}")

            # Publish the itineraries to the response queue with correlation_id
            for itinerary in itineraries:
                itinerary_json = itinerary.json()
                self.__msg_middleware.publish_message(
                    response_queue,
                    itinerary_json,
                    properties={"correlation_id": correlation_id}
                )
                logger.info(f"Published itinerary in Queue {response_queue} with correlation_id {correlation_id}: {itinerary_json}")

        except Exception as e:
            logger.error(f"Failed to process message: {e}")
    
    # def __process_response(self, response_data: str, properties: dict) -> None:
    #     try:
    #         correlation_id = properties.corelation_id
    #         if not correlation_id:
    #             logger.warning("Response received without correlation_id. Ignoring.")
    #             return

    #         logger.debug(f"Received response with correlation_id {correlation_id}: {response_data}")

    #         # Store the response in the temporary storage
    #         self.__response_storage[correlation_id] = response_data
    #     except Exception as e:
    #         logger.error(f"Failed to process response: {e}")
    
    def run(self):
        logger.info("Book Service initialized")
        self.__msg_middleware.consume_messages(self.__queue_callbacks)
        self.__msg_middleware.start_consuming()

def main() -> None: 
    initialize_dependencies()

    book_svc = BookSvc()
    book_svc.run()




