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
            INSERT INTO reservations (
                client_id,
                number_of_passengers,
                number_of_cabinets,
                itinerary_id,
                total_price
            )
            VALUES (
                {reservation_dto.client_id},
                {reservation_dto.number_of_passengers},
                {reservation_dto.number_of_cabinets},
                {reservation_dto.itinerary_id},
                {reservation_dto.total_price}
            )
            RETURNING
                id,
                client_id,
                number_of_passengers,
                number_of_cabinets,
                itinerary_id,
                total_price,
                reservation_status,
                ticket_status,
                payment_status
        """
        row = self.__database.execute_query(query)[0]

        reservation = Reservation(**row)

        logger.debug(f"Reservation created with ID: '{reservation.id}'")

        return reservation

    def update_status(self, reservation_id: int, new_status: str) -> Reservation:
        query = f"""
            UPDATE reservations
            SET
                reservation_status = '{new_status}',
                updated_at = transaction_timestamp()
            WHERE
                id = {reservation_id}
            RETURNING
                id,
                client_id,
                number_of_passengers,
                number_of_cabinets,
                itinerary_id,
                total_price,
                reservation_status,
                ticket_status,
                payment_status
        """
        row = self.__database.execute_query(query)[0]

        reservation = Reservation(**row)

        logger.debug(f"Reservation with ID '{reservation.id}' has been updated to -> '{new_status}'.")

        return reservation
