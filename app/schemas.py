from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserLogin(BaseModel):
    username: str
    password: str  # In production, add validation + hashing

class UserCreate(BaseModel):
    username: str
    password: str

class AuctionCreate(BaseModel):
    title: str
    description: str
    starting_price: float
    duration_hours: int  # e.g., 24 hours

class BidInput(BaseModel):
    amount: float
    user_id: int

class BidResponse(BaseModel):
    id: int
    amount: float
    user_id: int
    timestamp: datetime
    is_flagged: bool
    
    class Config:
        from_attributes = True

class AuctionResponse(BaseModel):
    id: int
    title: str
    description: str
    starting_price: float
    current_bid: float
    end_time: datetime
    is_active: bool
    seller_id: int
    ai_prediction: Optional[float] = None
    ai_analysis: Optional[dict] = None
    
    class Config:
        from_attributes = True