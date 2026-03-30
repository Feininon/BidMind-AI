from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./bidmind.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)  # In production, use proper hashing!
    balance = Column(Float, default=1000.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    bids = relationship("Bid", back_populates="user")
    auctions = relationship("Auction", back_populates="seller")

class Auction(Base):
    __tablename__ = "auctions"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    starting_price = Column(Float)
    current_bid = Column(Float, default=0.0)
    end_time = Column(DateTime)  # When auction closes
    is_active = Column(Boolean, default=True)
    seller_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    seller = relationship("User", back_populates="auctions")
    bids = relationship("Bid", back_populates="auction", order_by="Bid.timestamp.desc()")

class Bid(Base):
    __tablename__ = "bids"
    id = Column(Integer, primary_key=True, index=True)
    auction_id = Column(Integer, ForeignKey("auctions.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_flagged = Column(Boolean, default=False)  # AI fraud flag
    
    auction = relationship("Auction", back_populates="bids")
    user = relationship("User", back_populates="bids")

Base.metadata.create_all(bind=engine)