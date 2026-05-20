import os
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional
from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

app = FastAPI(title="Ava Real Estate Voice Agent API")

# ==========================================
# 💾 DATABASE SETUP
# ==========================================
DATABASE_URL = os.environ.get("NEON_DATABASE_URL")

engine = create_engine(DATABASE_URL)
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
    property_id: int
    city: str
    district: str
    property_type: str
    built_up_area_sqft: float
    price_inr: float
    bedrooms: int

class LeadCreate(BaseModel):
    name: str
    email: str
    phone: str
    budget: float

class Lead(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    email: str
    phone: str
    budget: float

class AppointmentCreate(BaseModel):
    lead_id: UUID
    property_id: int  
    appointment_time: datetime
    notes: Optional[str] = None

class Appointment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    lead_id: UUID
    property_id: int  
    appointment_time: datetime
    status: str = "Scheduled"
    notes: Optional[str] = None

# ==========================================
# 🛣️ FASTAPI ROUTES
# ==========================================
@app.get("/properties", response_model=list[PropertyResponse])
def get_properties(
    city: str = Query(None), 
    max_price: float = Query(None), 
    min_bedrooms: int = Query(None),
    db: Session = Depends(get_db)
):
    query_string = "SELECT property_id, city, district, property_type, built_up_area_sqft, price_inr, bedrooms FROM properties WHERE 1=1"
    params = {}
    
    if city:
        query_string += " AND LOWER(city) = LOWER(:city)"
        params["city"] = city
    if max_price:
        query_string += " AND price_inr <= :max_price"
        params["max_price"] = max_price
    if min_bedrooms:
        query_string += " AND bedrooms >= :min_bedrooms"
        params["min_bedrooms"] = min_bedrooms
        
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
            "bedrooms": row[6]
        })
        
    return properties_list

@app.post("/leads", response_model=Lead)
def create_lead(lead_data: LeadCreate):
    new_id = uuid4()
    full_lead = Lead(id=new_id, **lead_data.model_dump())
    db_leads[new_id] = full_lead
    return full_lead

@app.post("/appointments", response_model=Appointment)
def schedule_appointment(appointment_data: AppointmentCreate):
    new_id = uuid4()
    full_appointment = Appointment(id=new_id, **appointment_data.model_dump())
    db_appointments[new_id] = full_appointment
    return full_appointment