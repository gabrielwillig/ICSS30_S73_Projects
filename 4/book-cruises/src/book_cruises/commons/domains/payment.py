from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import json

class Payment(BaseModel):
    """Model representing a payment for cruise booking"""
    payment_id: str
    trip_id: str
    price: float
    passengers: int
    status: str = "processing"
    created_at: Optional[str] = None
    
    def __init__(self, **data):
        if "created_at" not in data:
            data["created_at"] = datetime.now().isoformat()
        super().__init__(**data)
    
    def dict(self, *args, **kwargs):
        """Override dict method to ensure proper serialization"""
        payment_dict = super().dict(*args, **kwargs)
        return payment_dict
    
    def json(self, *args, **kwargs):
        """Serialize to JSON string"""
        return json.dumps(self.dict(), *args, **kwargs)
    
    @classmethod
    def from_json(cls, json_str):
        """Create Payment object from JSON string"""
        data = json.loads(json_str)
        return cls(**data)
    
    @classmethod
    def from_dict(cls, data):
        """Create Payment object from dictionary"""
        return cls(**data)