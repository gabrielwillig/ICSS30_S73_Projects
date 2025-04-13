import json
from book_cruises.commons.utils import logger

class Itinerary:
    def __init__(self, destination: str, date: str, harbor: str):
        self.destination = destination
        self.date = date
        self.harbor = harbor

        self.validate()

    def validate(self):
        if not self.destination or not self.date or not self.harbor:
            raise ValueError("All fields must be provided.")

    @staticmethod
    def from_json_string(json_string: str) -> "Itinerary":
        data = json.loads(json_string)
        return Itinerary(**data)
