import inject

from book_cruises.commons.domains import Reservation, ReservationDTO
from book_cruises.commons.database import Database
from book_cruises.commons.utils import logger

class ReservationRepository:
    @inject.autoparams()
    def __init__(self, database: Database):
        self.__database = database

    def create_reservation(self, reservation_dto: ReservationDTO) -> Reservation:
        query = f"""
            INSERT INTO reservations (client_id, number_of_guests, itinerary_id, total_price)
            VALUES ({reservation_dto.client_id}, {reservation_dto.number_of_guests}, {reservation_dto.itinerary_id}, {reservation_dto.total_price})
            RETURNING id, client_id, number_of_guests, itinerary_id, created_at, total_price, status
        """
        result = self.__database.execute_query(query)

        reservation = Reservation(
            id=result[0]["id"],
            client_id=result[0]["client_id"],
            number_of_guests=result[0]["number_of_guests"],
            itinerary_id=result[0]["itinerary_id"],
            created_at=result[0]["created_at"].isoformat(),
            total_price=result[0]["total_price"],
            status=result[0]["status"],  # Default status, can be updated later
        )

        logger.debug(f"Reservation created with ID: {result[0]['id']}")

        return reservation