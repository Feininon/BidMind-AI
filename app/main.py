from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import json
import hashlib

from app import database, schemas, services

app = FastAPI(title="BidMind AI Engine")

# Mount Static Files (Frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# DB Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Simple Auth Helper (For demo - use JWT in production)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_current_user(user_id: int, db: Session):
    user = db.query(database.User).filter(database.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# WebSocket Manager (Updated to track auction rooms)
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, List[WebSocket]] = {}  # auction_id -> [sockets]
    
    async def connect(self, websocket: WebSocket, auction_id: int):
        await websocket.accept()
        if auction_id not in self.active_connections:
            self.active_connections[auction_id] = []
        self.active_connections[auction_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, auction_id: int):
        if auction_id in self.active_connections:
            if websocket in self.active_connections[auction_id]:
                self.active_connections[auction_id].remove(websocket)
            if not self.active_connections[auction_id]:
                del self.active_connections[auction_id]
    
    async def broadcast(self, auction_id: int, message: dict):
        if auction_id in self.active_connections:
            for connection in self.active_connections[auction_id]:
                await connection.send_json(message)

manager = ConnectionManager()

# ============ AUTH ENDPOINTS ============
@app.post("/auth/register")
async def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if username exists
    existing = db.query(database.User).filter(database.User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    new_user = database.User(
        username=user.username,
        password_hash=hash_password(user.password),
        balance=1000.0  # Demo: free starting balance
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"user_id": new_user.id, "username": new_user.username}

@app.post("/auth/login")
async def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(database.User).filter(database.User.username == user.username).first()
    if not db_user or db_user.password_hash != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"user_id": db_user.id, "username": db_user.username, "balance": db_user.balance}

# ============ AUCTION ENDPOINTS ============
@app.post("/api/auctions", response_model=schemas.AuctionResponse)
async def create_auction(auction: schemas.AuctionCreate, db: Session = Depends(get_db)):
    # Gen AI Analysis on Description
    ai_analysis = await services.analyze_item_groq(auction.description)
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(hours=auction.duration_hours)
    
    db_auction = database.Auction(
        title=auction.title,
        description=auction.description,
        starting_price=auction.starting_price,
        current_bid=auction.starting_price,
        end_time=end_time,
        seller_id=1,  # Demo: default seller
        is_active=True
    )
    db.add(db_auction)
    db.commit()
    db.refresh(db_auction)
    
    # Get AI price prediction
    ai_prediction = services.predict_price(auction.starting_price, auction.duration_hours)
    
    return {
        **db_auction.__dict__,
        "ai_prediction": ai_prediction,
        "ai_analysis": ai_analysis
    }

@app.get("/api/auctions", response_model=List[schemas.AuctionResponse])
async def list_auctions(active_only: bool = True, db: Session = Depends(get_db)):
    query = db.query(database.Auction)
    if active_only:
        query = query.filter(database.Auction.is_active == True)
    auctions = query.all()
    
    results = []
    for a in auctions:
        pred = services.predict_price(a.starting_price, (a.end_time - datetime.utcnow()).total_seconds() / 3600)
        results.append({**a.__dict__, "ai_prediction": pred})
    return results

@app.get("/api/auctions/{auction_id}", response_model=schemas.AuctionResponse)
async def get_auction(auction_id: int, db: Session = Depends(get_db)):
    auction = db.query(database.Auction).filter(database.Auction.id == auction_id).first()
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    
    pred = services.predict_price(auction.starting_price, (auction.end_time - datetime.utcnow()).total_seconds() / 3600)
    return {**auction.__dict__, "ai_prediction": pred}

@app.get("/api/auctions/{auction_id}/history")
async def get_bid_history(auction_id: int, db: Session = Depends(get_db)):
    bids = db.query(database.Bid).filter(
        database.Bid.auction_id == auction_id
    ).order_by(database.Bid.timestamp.desc()).all()
    
    return [
        {
            "id": b.id,
            "amount": b.amount,
            "user_id": b.user_id,
            "timestamp": b.timestamp,
            "is_flagged": b.is_flagged
        }
        for b in bids
    ]

@app.get("/api/users/{user_id}/history")
async def get_user_history(user_id: int, db: Session = Depends(get_db)):
    # Get user's bids
    bids = db.query(database.Bid).filter(database.Bid.user_id == user_id).all()
    # Get user's created auctions
    auctions = db.query(database.Auction).filter(database.Auction.seller_id == user_id).all()
    
    return {
        "bids": [
            {"auction_id": b.auction_id, "amount": b.amount, "timestamp": b.timestamp, "won": False}
            for b in bids
        ],
        "auctions": [
            {"id": a.id, "title": a.title, "final_price": a.current_bid, "status": "active" if a.is_active else "closed"}
            for a in auctions
        ]
    }

# ============ WEBSOCKET BID ENDPOINT ============
@app.websocket("/ws/bid/{auction_id}")
async def websocket_bid(websocket: WebSocket, auction_id: int):
    await manager.connect(websocket, auction_id)
    
    # Send initial auction state
    db = database.SessionLocal()
    auction = db.query(database.Auction).filter(database.Auction.id == auction_id).first()
    
    if auction:
        await websocket.send_json({
            "type": "init",
            "auction": {
                "id": auction.id,
                "title": auction.title,
                "current_bid": auction.current_bid,
                "end_time": auction.end_time.isoformat(),
                "ai_prediction": services.predict_price(auction.starting_price, auction.id)
            }
        })
    
    try:
        while True:
            data = await websocket.receive_text()
            bid_data = json.loads(data)
            
            # Re-fetch auction to get latest state
            auction = db.query(database.Auction).filter(database.Auction.id == auction_id).first()
            if not auction or not auction.is_active:
                await websocket.send_json({"status": "error", "message": "Auction closed"})
                continue
            
            # Check time
            if datetime.utcnow() > auction.end_time:
                auction.is_active = False
                db.commit()
                await manager.broadcast(auction_id, {"type": "auction_ended", "winner": "TBD"})
                continue
            
            # AI Fraud Check
            time_left = (auction.end_time - datetime.utcnow()).total_seconds() / 60
            is_fraud = services.detect_fraud(bid_data['amount'], time_left, bid_data['user_id'])
            
            if is_fraud:
                await websocket.send_json({"status": "rejected", "reason": "🤖 AI Fraud Detection Flagged"})
                continue
            
            # Check bid > current
            if bid_data['amount'] <= auction.current_bid:
                await websocket.send_json({"status": "rejected", "reason": "Bid must be higher than current"})
                continue
            
            # Update auction
            auction.current_bid = bid_data['amount']
            db.commit()
            
            # Record bid
            new_bid = database.Bid(
                auction_id=auction_id,
                user_id=bid_data['user_id'],
                amount=bid_data['amount'],
                is_flagged=False
            )
            db.add(new_bid)
            db.commit()
            
            # Update AI prediction with new state
            updated_pred = services.predict_price(auction.starting_price, time_left / 60)
            
            # Broadcast to all viewers
            await manager.broadcast(auction_id, {
                "type": "bid_update",
                "amount": bid_data['amount'],
                "user_id": bid_data['user_id'],
                "current_bid": auction.current_bid,
                "ai_prediction": updated_pred,
                "time_left_seconds": max(0, (auction.end_time - datetime.utcnow()).total_seconds()),
                "fraud_check": "passed"
            })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, auction_id)
    finally:
        db.close()

# ============ FRONTEND ROUTES (Fixed for Windows) ============

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    with open("static/dashboard.html", encoding="utf-8") as f:
        return f.read()

@app.get("/create", response_class=HTMLResponse)
async def create_page():
    with open("static/create.html", encoding="utf-8") as f:
        return f.read()

@app.get("/auction/{auction_id}", response_class=HTMLResponse)
async def auction_page(auction_id: int):
    with open("static/auction.html", encoding="utf-8") as f:
        content = f.read()
        return content.replace("{{AUCTION_ID}}", str(auction_id))

@app.get("/history", response_class=HTMLResponse)
async def history_page():
    with open("static/history.html", encoding="utf-8") as f:
        return f.read()