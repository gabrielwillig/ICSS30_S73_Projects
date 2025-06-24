from typing import Annotated, Optional, Union, List
from datetime import date, time

from pydantic import BaseModel, Field, AfterValidator, field_validator

FormattedStr = Annotated[str, AfterValidator(lambda v: v.strip().lower())]
FormattedList = Annotated[
    list[str], AfterValidator(lambda v: [x.strip().lower() for x in v])
]


class Itinerary(BaseModel):
    id: Optional[int] = Field(None, description="Unique identifier for the itinerary")
    ship: Optional[FormattedStr] = Field(None, description="Name of the ship")
    departure_date: Union[date, str] = Field(description="Departure date")
    departure_time: Union[time, str] = Field(description="Departure time")
    departure_harbor: FormattedStr = Field(description="Departure harbor")
    arrival_harbor: FormattedStr = Field(description="Arrival harbor")
    arrival_date: Union[date, str] = Field(description="Arrival date")
    visiting_harbors: FormattedList = Field(
        default_factory=list, description="List of visiting harbors"
    )
    number_of_days: int = Field(description="Number of days for the itinerary")
    remaining_cabinets: int = Field(
        description="Remaining seats available for the itinerary"
    )
    remaining_passengers: int = Field(
        description="Remaining passengers available for the itinerary"
    )
    price: float = Field(description="Price of the itinerary")

    def __init__(self, **data):
        super().__init__(**data)

        if isinstance(self.departure_date, date):
            self.departure_date = (
                self.departure_date.isoformat()
            )  # Convert date to ISO format string
        if isinstance(self.arrival_date, date):
            self.arrival_date = (
                self.arrival_date.isoformat()
            )  # Convert date to ISO format string
        if isinstance(self.departure_time, time):
            self.departure_time = self.departure_time.isoformat()


class ItineraryDTO(BaseModel):
    id: Optional[int] = Field(None, description="Unique identifier for the itinerary")
    ship: Optional[str] = Field(None, description="Name of the ship")
    departure_harbor: str = Field(description="Departure harbor")
    departure_date: Union[date, str] = Field(description="Departure date")
    departure_time: Optional[Union[time, str]] = Field(
        None, description="Departure time"
    )
    arrival_harbor: str = Field(description="Arrival harbor")
    arrival_date: Optional[Union[date, str]] = Field(None, description="Arrival date")
    visiting_harbors: Optional[List[str]] = Field(
        default_factory=list, description="List of visiting harbors"
    )
    number_of_days: Optional[int] = Field(
        None, description="Number of days for the itinerary"
    )
    price: Optional[float] = Field(None, description="Price of the itinerary")
    remaining_seats: Optional[int] = Field(
        default=None, description="Remaining seats available for the itinerary"
    )
