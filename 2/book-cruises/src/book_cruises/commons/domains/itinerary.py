from typing import Annotated, Optional, Union
from datetime import date, datetime
from pydantic import BaseModel, Field, AfterValidator
from book_cruises.commons.utils import logger
from .itinerary_dto import ItineraryDTO

FormattedStr = Annotated[str, AfterValidator(lambda v: v.strip().lower())]
FormattedList = Annotated[list[str], AfterValidator(lambda v: [x.strip().lower() for x in v])]


class Itinerary(BaseModel):
    id: Optional[int] = Field(None, description="Unique identifier for the itinerary")
    ship: Optional[FormattedStr] = Field(None, description="Name of the ship")
    departure_date: date = Field(description="Departure date")
    departure_harbor: FormattedStr = Field(description="Departure harbor")
    departure_time: datetime = Field(description="Departure time")
    arrival_harbor: FormattedStr = Field(description="Arrival harbor")
    arrival_date: date = Field(description="Arrival date")
    visiting_harbors: FormattedList = Field(
        default_factory=list, description="List of visiting harbors"
    )
    number_of_days: int = Field(description="Number of days for the itinerary")
    price: float = Field(description="Price of the itinerary")

    @staticmethod
    def from_dto(dto: "ItineraryDTO") -> "Itinerary":
        raise NotImplementedError("Mapping logic not implemented yet")
        return Itinerary(
            id=dto.id,
            ship=dto.ship,
            departure_date=dto.departure_date,
            departure_harbor=dto.departure_harbor,
            departure_time=dto.departure_time,
            arrival_harbor=dto.arrival_harbor,
            arrival_time=dto.arrival_time,
            visiting_harbors=dto.visiting_harbors,
            number_of_days=dto.number_of_days,
            price=dto.price,
        )

    def to_dto(self) -> "ItineraryDTO":
        return ItineraryDTO(
            id=self.id,
            ship=self.ship,
            departure_date=self.departure_date,
            departure_harbor=self.departure_harbor,
            departure_time=self.departure_time,
            arrival_harbor=self.arrival_harbor,
            arrival_time=self.arrival_time,
            visiting_harbors=self.visiting_harbors,
            number_of_days=self.number_of_days,
            price=self.price,
        )
