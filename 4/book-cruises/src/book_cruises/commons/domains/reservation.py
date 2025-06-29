from typing import Optional, ClassVar

from pydantic import BaseModel, Field, model_validator

from .itinerary import Itinerary


class Reservation(BaseModel):
    APPROVED: ClassVar[str] = "APPROVED"
    CANCELLED: ClassVar[str] = "CANCELLED"
    PENDING: ClassVar[str] = "PENDING"

    id: int = Field(description="Unique identifier for the reservation")
    client_id: str = Field(description="Unique identifier for the client")
    number_of_passengers: int = Field(
        description="Number of passengers included in the reservation"
    )
    number_of_cabinets: int = Field(description="Number of cabinets reserved")
    itinerary_id: int = Field(description="Identifier for the itinerary")
    reservation_status: str = Field(description="Status of the reservation")
    ticket_status: str = Field(description="Status of the ticket generation")
    payment_status: str = Field(description="Status of the payment")
    itinerary: Optional[Itinerary] = Field(
        default=None, description="Full itinerary info"
    )
    total_price: Optional[float] = Field(
        default=None, description="Total price for the reservation"
    )

    @model_validator(mode="after")
    def retrieve_itinerary(cls, reservation: "Reservation") -> "Reservation":
        from .repositories import ItineraryRepository

        if reservation.itinerary_id is None:
            raise ValueError("Itinerary ID is required to retrieve itinerary details.")

        if not reservation.itinerary:
            itinerary = ItineraryRepository().get_by_id(reservation.itinerary_id)
            if not itinerary:
                raise ValueError(
                    f"Itinerary with id {reservation.itinerary_id} not found."
                )
            reservation.itinerary = itinerary
        return reservation


class ReservationDTO(BaseModel):
    client_id: str = Field(description="Unique identifier for the client")
    number_of_passengers: int = Field(
        description="Number of passengers included in the reservation"
    )
    number_of_cabinets: int = Field(description="Number of cabinets reserved")
    itinerary_id: int = Field(description="Itinerary ID for the reservation")
    total_price: float = Field(description="Total price for the reservation")
