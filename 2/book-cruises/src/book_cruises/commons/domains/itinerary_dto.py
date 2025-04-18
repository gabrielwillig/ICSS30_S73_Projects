from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import List, Optional, Union


class ItineraryDTO(BaseModel):
    id: Optional[int] = Field(None, description="Unique identifier for the itinerary")
    ship: Optional[str] = Field(None, description="Name of the ship")
    departure_harbor: str = Field(description="Departure harbor")
    departure_date: Union[date, str] = Field(description="Departure date")
    departure_time: Optional[Union[datetime, str]] = Field(None, description="Departure time")
    arrival_harbor: str = Field(description="Arrival harbor")
    arrival_date: Optional[Union[datetime, str]] = Field(None, description="Arrival date")
    visiting_harbors: Optional[List[str]] = Field(
        default_factory=list, description="List of visiting harbors"
    )
    number_of_days: Optional[int] = Field(None, description="Number of days for the itinerary")
    price: Optional[float] = Field(None, description="Price of the itinerary")

    @field_validator("departure_date", "arrival_date", "departure_time", mode="before")
    def validate_date_or_datetime(cls, value, field):
        if isinstance(value, str):
            try:
                if field == "departure_time":
                    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                else:
                    return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"{field} must be in YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format.")
        return value
