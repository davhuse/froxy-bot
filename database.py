import os
from sqlalchemy import create_engine, Column, Integer, Float, DateTime, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# SQLite veritabanı dosyası proje dizininde oluşturulacak
DB_URL = "sqlite:///bot_database.db"

engine = create_engine(DB_URL, echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = "users"

    telegram_id = Column(Integer, primary_key=True, index=True)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class PaymentRequest(Base):
    __tablename__ = "payment_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    amount = Column(Float)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_user(telegram_id: int):
    session = SessionLocal()
    user = session.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id)
        session.add(user)
        session.commit()
        session.refresh(user)
    session.close()
    return user
