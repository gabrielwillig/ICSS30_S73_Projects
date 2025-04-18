from book_cruises.commons.domains import Itinerary, ItineraryDTO
from book_cruises.commons.utils import Database

class ItineraryRepository:
    def __init__(self, database: Database):
        self.__database = database

    def get_itineraries(self, itinerary_dto: ItineraryDTO) -> list[Itinerary]:
        query = f"""
            SELECT * FROM itineraries
            WHERE arrival_harbor = '{itinerary_dto.arrival_harbor}'
                AND departure_date = '{itinerary_dto.departure_date}'
                AND departure_harbor = '{itinerary_dto.departure_harbor}'
        """
        results = self.__database.execute_query(query)
        if not results:
            return []

        # Map database rows to Itinerary domain objects
        itineraries = []
        for row in results:
            itinerary = Itinerary(
                id=row["id"],
                ship=row["ship"],
                departure_date=row["departure_date"],
                departure_harbor=row["departure_harbor"],
                departure_time=row["departure_time"],
                arrival_harbor=row["arrival_harbor"],
                arrival_time=row["arrival_time"],
                visiting_harbors=row["visiting_harbors"].split(","),
                number_of_days=row["number_of_days"],
                price=row["price"]
            )
            itineraries.append(itinerary)

        return itineraries