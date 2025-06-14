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

        logger.debug(f"Results: '{results}'")

        # Map database rows to Itinerary domain objects
        itineraries = []
        for row in results:
            itinerary = Itinerary(**row)
            itineraries.append(itinerary)

        return itineraries

    def get_by_id(self, itinerary_id: int) -> Itinerary | None:
        query = f"SELECT * FROM itineraries WHERE id = {itinerary_id}"
        result = self.__database.execute_query(query)

        if not result:
            logger.error(f"Itinerary with ID '{itinerary_id}' not found.")
            return

        row = result[0]
        itinerary = Itinerary(**row)

        logger.debug(f"Retrieved itinerary: '{itinerary}'")

        return itinerary

    def update_remaining_cabinets(
        self, itinerary_id: int, requested_cabinets: int
    ) -> None:
        query = f"""
            UPDATE itineraries
            SET remaining_cabinets = remaining_cabinets - {requested_cabinets},
                updated_at = transaction_timestamp()
            WHERE id = {itinerary_id} AND remaining_cabinets >= {requested_cabinets}
        """
        rows_affected = self.__database.execute_query(query)

        if rows_affected == 0:
            logger.error(
                f"Failed to update remaining cabinets for itinerary ID '{itinerary_id}'."
            )
        else:
            logger.debug(
                f"Successfully updated remaining cabinets for itinerary ID '{itinerary_id}'."
            )
