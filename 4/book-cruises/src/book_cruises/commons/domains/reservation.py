from typing import Optional

from pydantic import BaseModel, Field, model_validator

from .itinerary import Itinerary


class Reservation(BaseModel):
    id: int = Field(description="Unique identifier for the reservation")
    client_id: int = Field(description="Unique identifier for the client")
    number_of_guests: int = Field(description="Number of guests included in the reservation")
    itinerary_id: int = Field(description="Identifier for the itinerary")
    created_at: str = Field(description="Creation timestamp")
    status: str = Field(description="Status of the reservation")
    itinerary: Optional[Itinerary] = Field(default=None, description="Full itinerary info")
    total_price: Optional[float] = Field(default=None, description="Total price for the reservation")

    @model_validator(mode="after")
    def retrieve_itinerary(cls, reservation: "Reservation") -> "Reservation":
        from .repositories import ItineraryRepository

        if reservation.itinerary_id is None:
            raise ValueError("Itinerary ID is required to retrieve itinerary details.")

        if not reservation.itinerary:
            itinerary = ItineraryRepository().get_by_id(reservation.itinerary_id)
            if not itinerary:
                raise ValueError(f"Itinerary with id {reservation.itinerary_id} not found.")
            reservation.itinerary = itinerary
        return reservation


class ReservationDTO(BaseModel):
    client_id: int = Field(description="Unique identifier for the client")
    number_of_guests: int = Field(description="Number of guests included in the reservation")
    itinerary_id: int = Field(description="Itinerary ID for the reservation")
    total_price: float = Field(description="Total price for the reservation")
