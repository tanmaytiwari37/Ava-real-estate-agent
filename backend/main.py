import os
import socket
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
from livekit.api import AccessToken, VideoGrants

# Force socket to resolve ONLY IPv4 for Neon host to prevent local network IPv6 routing issues on developer machine
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    if host and "neon.tech" in host:
        return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return orig_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = getaddrinfo_ipv4

# ==========================================
# 💾 DATABASE SETUP & dotenv loading
# ==========================================
# Load environment variables (from local or voice_agent directory)
load_dotenv(override=True)
load_dotenv("../voice_agent/.env", override=True)

app = FastAPI(title="Ava Real Estate Voice Agent API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_leads = {}
db_appointments = {}

# ==========================================
# 📋 PYDANTIC SCHEMAS
# ==========================================
class PropertyResponse(BaseModel):
    property_id: str
    city: str
    district: str
    property_type: str
    built_up_area_sqft: float
    price_inr: float
    monthly_rental_estimate_inr: float
    bedrooms: int
    status: str

class LeadCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    budget: Optional[float] = None

class Lead(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    phone: str
    email: Optional[str] = None
    budget: Optional[float] = None

class AppointmentCreate(BaseModel):
    lead_id: UUID
    property_id: str        # ✅ Fixed: was int, now str to match "PROP00001" format
    appointment_time: datetime
    notes: Optional[str] = None

class Appointment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    lead_id: UUID
    property_id: str        # ✅ Fixed: was int, now str
    appointment_time: datetime
    status: str = "Scheduled"
    notes: Optional[str] = None

# ==========================================
# 🛣️ FASTAPI ROUTES
# ==========================================
@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Ava Real Estate CRM API is running successfully!",
        "docs_url": "http://127.0.0.1:8000/docs",
        "endpoints": {
            "token": "/token",
            "properties": "/properties",
            "leads": "/leads",
            "appointments": "/appointments"
        }
    }


@app.get("/token")
def get_token(room_name: str = "ava-room", identity: str = None):
    if not identity:
        identity = f"user_{uuid4().hex[:6]}"
        
    api_key = os.environ.get("LIVEKIT_API_KEY")
    api_secret = os.environ.get("LIVEKIT_API_SECRET")
    
    if not api_key or not api_secret:
        return {"error": "LiveKit credentials not configured in server environment"}
        
    token = AccessToken(api_key, api_secret)
    token.with_identity(identity)
    
    grants = VideoGrants(
        room_join=True,
        room=room_name
    )
    token.with_grants(grants)
    
    return {
        "token": token.to_jwt(),
        "url": os.environ.get("LIVEKIT_URL", "wss://your-project.livekit.cloud")
    }

@app.get("/properties", response_model=list[PropertyResponse])
def get_properties(
    city: str = Query(None),
    max_price: float = Query(None),
    min_bedrooms: int = Query(None),
    property_type: str = Query(None),
    purpose: str = Query("buy"),
    db: Session = Depends(get_db)
):
    query_string = (
        "SELECT property_id, city, district, property_type, "
        "built_up_area_sqft, price_inr, monthly_rental_estimate_inr, bedrooms, status "
        "FROM properties WHERE LOWER(status) = 'available'"
    )
    params = {}

    if city:
        query_string += " AND LOWER(city) = LOWER(:city)"
        params["city"] = city

    if max_price:
        if purpose.lower() == "rent":
            query_string += " AND monthly_rental_estimate_inr <= :max_price"
        else:
            query_string += " AND price_inr <= :max_price"
        params["max_price"] = max_price

    if min_bedrooms:
        query_string += " AND bedrooms >= :min_bedrooms"
        params["min_bedrooms"] = min_bedrooms

    if property_type:
        query_string += " AND LOWER(property_type) = LOWER(:property_type)"
        params["property_type"] = property_type

    query_string += " LIMIT 5"

    result = db.execute(text(query_string), params)

    properties_list = []
    for row in result:
        properties_list.append({
            "property_id": row[0],
            "city": row[1],
            "district": row[2],
            "property_type": row[3],
            "built_up_area_sqft": row[4],
            "price_inr": row[5],
            "monthly_rental_estimate_inr": row[6],
            "bedrooms": row[7],
            "status": row[8],
        })

    return properties_list


@app.post("/leads", response_model=Lead)
def create_lead(lead_data: LeadCreate):
    new_id = uuid4()
    full_lead = Lead(id=new_id, **lead_data.model_dump())
    db_leads[new_id] = full_lead
    return full_lead


@app.get("/leads", response_model=list[Lead])
def get_leads():
    return list(db_leads.values())


@app.post("/appointments", response_model=Appointment)
def schedule_appointment(appointment_data: AppointmentCreate):
    new_id = uuid4()
    full_appointment = Appointment(id=new_id, **appointment_data.model_dump())
    db_appointments[new_id] = full_appointment
    return full_appointment


@app.get("/appointments", response_model=list[Appointment])
def get_appointments():
    return list(db_appointments.values())