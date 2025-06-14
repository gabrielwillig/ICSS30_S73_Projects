import uuid

from pydantic import BaseModel, Field

from .payment import Payment


class Ticket(BaseModel):
    id: int = Field(description="Unique identifier for the Ticket")
    status: str = Field(
        default="pending",
        description="Status of the payment (e.g., pending, approved, refused)",
    )
    payment: Payment = Field(
        description="Payment details associated with this ticket"
    )

    @staticmethod
    def create_ticket(
        payment: Payment
    ) -> "Ticket":
        """
        Factory method to create a Payment instance from a reservation.
        """
        return Ticket(
            id=uuid.uuid4().int,
            status="pending",
            payment=payment,
        )
