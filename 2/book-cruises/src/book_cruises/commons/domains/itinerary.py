from book_cruises.commons.utils import logger 

class Itinerary:
    def __init__(self, destination: str, date: str, harbor: str):
        self.destination = destination
        self.date = date
        self.harbor = harbor
        self.validate()
    
    def validate(self):
        if not self.destination or not self.date or not self.harbor:
            logger.error("Destination, date, and harbor must be provided.")
            return False