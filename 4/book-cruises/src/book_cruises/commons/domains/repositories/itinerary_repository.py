import inject

from book_cruises.commons.domains import Itinerary, ItineraryDTO
from book_cruises.commons.database import Database
from book_cruises.commons.utils import logger

class ItineraryRepository:
    @inject.autoparams()
    def __init__(self, database: Database):
        self.__database = database

    def get_itineraries(self, itinerary_dto: ItineraryDTO) -> list[Itinerary]:
        query = f"""
            SELECT * FROM itineraries
            WHERE LOWER(arrival_harbor) = LOWER('{itinerary_dto.arrival_harbor}')
                AND departure_date = TO_DATE('{itinerary_dto.departure_date}', 'YYYY-MM-DD')
                AND LOWER(departure_harbor) = LOWER('{itinerary_dto.departure_harbor}')
        """
        results = self.__database.execute_query(query)
        if not results:
            return []

        logger.debug(f"results: {results}")

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
                arrival_date=row["arrival_date"],
                visiting_harbors=row["visiting_harbors"],
                number_of_days=row["number_of_days"],
                price=row["price"]
            )
            itineraries.append(itinerary)

        return itineraries

    def get_by_id(self, itinerary_id: int) -> Itinerary | None:
        query = f"SELECT * FROM itineraries WHERE id = {itinerary_id}"
        result = self.__database.execute_query(query)

        if not result:
            return None

        row = result[0]
        itinerary = Itinerary(
            id=row["id"],
            ship=row["ship"],
            departure_date=row["departure_date"],
            departure_harbor=row["departure_harbor"],
            departure_time=row["departure_time"],
            arrival_harbor=row["arrival_harbor"],
            arrival_date=row["arrival_date"],
            visiting_harbors=row["visiting_harbors"],
            number_of_days=row["number_of_days"],
            price=row["price"]
        )

        return itinerary