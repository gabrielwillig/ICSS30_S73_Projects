import inject
from .di import configure_dependencies
from book_cruises.commons.utils import MessageMidleware, Database, logger, config
from book_cruises.commons.domains import Itinerary

class BookSvc:
    @inject.autoparams()
    def __init__(self, msg_middleware: MessageMidleware, database: Database):
        self.msg_middleware = msg_middleware
        self.database = database
        logger.info("Book Service initialized")
    
    def process_itinerary(self, itinerary_data: str):
        try:
            # Create an Itinerary object
            itinerary_data = Itinerary.from_json_string(itinerary_data)
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
    
    def run(self):
        self.msg_middleware.consume_messages(self.process_itinerary)

def main(): 
    inject.configure(configure_dependencies)  # Initialize the DI container
    book_svc = BookSvc()
    book_svc.run()
        
        


