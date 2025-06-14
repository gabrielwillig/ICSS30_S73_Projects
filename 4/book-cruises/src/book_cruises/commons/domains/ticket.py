from typing import ClassVar
import uuid

from pydantic import BaseModel, Field

from .payment import Payment


class Ticket(BaseModel):
    GENERATED: ClassVar[str] = "GENERATED"
    PENDING: ClassVar[str] = "PENDING"

    id: int = Field(description="Unique identifier for the Ticket")
    status: str = Field(
        description="Status of the payment (e.g., pending, approved, refused)",
    )
    payment: Payment = Field(description="Payment details associated with this ticket")

    @staticmethod
    def create_ticket(payment: Payment) -> "Ticket":
        """
        Factory method to create a Payment instance from a reservation.
        """
        return Ticket(
            id=uuid.uuid4().int,
            status=Ticket.GENERATED,
            payment=payment,
        )
