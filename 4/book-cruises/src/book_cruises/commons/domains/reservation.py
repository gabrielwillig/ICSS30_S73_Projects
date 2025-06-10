from typing import Optional
from uuid import uuid4
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from .itinerary import Itinerary
from .repositories import ItineraryRepository


class Reservation(BaseModel):
    id: str = Field(default_factory=lambda: f"res-{str(uuid4())}", description="Unique identifier for the reservation")
    client_id: int = Field(description="Unique identifier for the client")
    number_of_guests: int = Field(description="Number of guests included in the reservation")
    itinerary_id: int = Field(description="Identifier for the itinerary")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Creation timestamp")
    itinerary: Optional[Itinerary] = Field(default=None, description="Full itinerary info")
    total_price: Optional[float] = Field(default=None, description="Total price for the reservation")

    @model_validator(mode="after")
    def retrieve_itinerary(cls, reservation: "Reservation") -> "Reservation":
        if reservation.itinerary_id is None:
            raise ValueError("Itinerary ID is required to retrieve itinerary details.")

        if not reservation.itinerary:
            itinerary = ItineraryRepository().get_by_id(reservation.itinerary_id)
            if not itinerary:
                raise ValueError(f"Itinerary with id {reservation.itinerary_id} not found.")
            reservation.itinerary = itinerary
        return reservation

    @model_validator(mode="after")
    def compute_total_price(cls, reservation: "Reservation") -> "Reservation":
        if reservation.total_price is None:
            if not reservation.itinerary or reservation.itinerary.price is None:
                raise ValueError("Itinerary with valid price is required to compute total price.")
            reservation.total_price = reservation.number_of_guests * reservation.itinerary.price
        return reservation


class ReservationDTO(BaseModel):
    client_id: int = Field(description="Unique identifier for the client")
    number_of_guests: int = Field(description="Number of guests included in the reservation")
    itinerary_id: int = Field(description="Itinerary ID for the reservation")

    def to_reservation(self) -> Reservation:
        return Reservation(
            client_id=self.client_id,
            number_of_guests=self.number_of_guests,
            itinerary_id=self.itinerary_id
        )


    # @staticmethod
    # def from_dto(dto: "ReservationDTO") -> "Reservation":
    #     return Reservation(
    #         id=dto.id,
    #         client_id=dto.client_id,
    #         number_of_guests=dto.number_of_guests,
    #         total_price=dto.total_price,
    #         itinerary=Itinerary.from_dto(dto.itinerary) if dto.itinerary else None
    #     )

    # def to_dto(self) -> "ReservationDTO":
    #     return ReservationDTO(
    #         id=self.id,
    #         client_id=self.client_id,
    #         number_of_guests=self.number_of_guests,
    #         total_price=self.total_price,
    #         itinerary=self.itinerary.to_dto() if self.itinerary else None
    #     )
