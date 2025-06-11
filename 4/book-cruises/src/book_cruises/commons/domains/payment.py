from typing import Optional
import uuid

from pydantic import BaseModel, Field


class Payment(BaseModel):
    id: int = Field(description="Unique identifier for the Payment")
    status: str = Field(
        default="pending",
        description="Status of the payment (e.g., pending, approved, refused)",
    )
    currency: str = Field(default="USD", description="Currency of the payment")
    total_price: float = Field(description="Price of the itinerary")
    reservation_id: int = Field(
        description="Identifier for the reservation associated with this payment"
    )
    itinerary_id: int = Field(
        description="Identifier for the itinerary associated with this payment"
    )
    client_id: int = Field(
        description="Unique identifier for the client making the payment"
    )

    @staticmethod
    def create_payment(
        reservation_id: int,
        itinerary_id: int,
        client_id: int,
        total_price: float,
        currency: Optional[str] = "USD",
    ) -> "Payment":
        """
        Factory method to create a Payment instance from a reservation.
        """
        return Payment(
            id=uuid.uuid4().int,
            status="pending",
            total_price=total_price,
            reservation_id=reservation_id,
            itinerary_id=itinerary_id,
            client_id=client_id,
            currency=currency,
        )
