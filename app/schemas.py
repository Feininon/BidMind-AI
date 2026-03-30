from pydantic import BaseModel
from typing import Optional

class BidInput(BaseModel):
    auction_id: int
    amount: float
    user_id: int
    user_agent: Optional[str] = "Web"

class AuctionCreate(BaseModel):
    title: str
    description: str
    starting_price: float