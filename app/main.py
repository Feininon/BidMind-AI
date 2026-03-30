from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List
import json

from app import database, schemas, services

app = FastAPI(title="BidMind AI Engine")

# Mount Frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# DB Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.get("/")
async def read_root():
    return {"message": "BidMind AI API Ready", "models_loaded": services.MODELS_LOADED}

@app.websocket("/ws/bid/{auction_id}")
async def websocket_endpoint(websocket: WebSocket, auction_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            bid_data = json.loads(data)
            
            # 1. AI Fraud Check
            is_fraud = services.detect_fraud(
                amount=bid_data['amount'], 
                time_left=bid_data.get('time_left', 60), 
                user_id=bid_data['user_id']
            )
            
            if is_fraud:
                await websocket.send_json({"status": "rejected", "reason": "AI Fraud Detection Flagged"})
                continue

            # 2. AI Price Prediction
            # Assuming you send starting_price & duration in the bid data for context
            predicted_close = services.predict_price(
                starting_price=bid_data.get('starting_price', 100), 
                duration_hours=bid_data.get('duration', 24)
            )

            # 3. Broadcast to all viewers
            await manager.broadcast({
                "type": "new_bid",
                "auction_id": auction_id,
                "amount": bid_data['amount'],
                "user_id": bid_data['user_id'],
                "ai_prediction": predicted_close,
                "fraud_check": "passed"
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/auctions")
async def create_auction(auction: schemas.AuctionCreate, db: Session = Depends(get_db)):
    # Gen AI Analysis on Creation
    ai_analysis = await services.analyze_item_groq(auction.description)
    
    db_auction = database.Auction(
        title=auction.title, 
        description=auction.description, 
        starting_price=auction.starting_price
    )
    db.add(db_auction)
    db.commit()
    db.refresh(db_auction)
    
    return {"data": db_auction, "ai_analysis": ai_analysis}