import datetime 
import inject
from .di import configure_dependencies
from book_cruises.commons.utils import MessageMidleware
from book_cruises.commons.utils import logger
from book_cruises.commons.domains import Itinerary
from book_cruises.commons.utils import config

class BookSvc:
    @inject.autoparams()
    def __init__(self, msg_middleware: MessageMidleware):
        self.msg_middleware = msg_middleware
        logger.info("Book Service initialized")

    def verify_itinerary(self, Itinerary: Itinerary):
        # TODO: Implement the logic to verify the itinerary.
        pass
        
    def run(self):
        pass

def main(): 
    inject.configure(configure_dependencies)  # Initialize the DI container
    book_svc = BookSvc()
    book_svc.run()
        
        


