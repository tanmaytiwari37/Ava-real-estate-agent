from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Initialize FastAPI App
app = FastAPI(
    title="Ava Real Estate CRM API",
    description="A dummy server for handling property listings, client leads, and viewing appointments.",
    version="1.0.0",
)

# ==========================================
# 📋 STEP 3A: DATA MODELS (Pydantic Schemas)
# ==========================================

class Property(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    location: str
    price: float
    bedrooms: int
    is_available: bool = True

class Lead(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    email: str
    phone: str
    budget: float

class AppointmentCreate(BaseModel):
    lead_id: UUID
    property_id: UUID
    appointment_time: datetime
    notes: Optional[str] = None

class Appointment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    lead_id: UUID
    property_id: UUID
    appointment_time: datetime
    status: str = "Scheduled"  # Scheduled, Completed, Cancelled
    notes: Optional[str] = None


# ==========================================
# 💾 STEP 3B: IN-MEMORY DATABASE (Mock Data)
# ==========================================

# Seed data so the API isn't empty when you start
db_properties = {
    uuid4(): Property(title="Luxury Penthouse", location="Downtown", price=1200000, bedrooms=3),
    uuid4(): Property(title="Cozy Suburban House", location="Greenfield", price=450000, bedrooms=4),
}

db_leads = {}
db_appointments = {}


# ==========================================
# 🚀 STEP 3C: API ROUTING / ENDPOINTS
# ==========================================

@app.get("/", tags=["Root"])
def root():
    return {"message": "Welcome to Ava Real Estate Agent CRM API", "docs": "/docs"}


# --- PROPERTIES ENDPOINTS ---

@app.get("/properties", response_model=List[Property], tags=["Properties"])
def get_properties():
    """Fetch all active real estate listings."""
    return list(db_properties.values())

@app.post("/properties", response_model=Property, status_code=status.HTTP_201_CREATED, tags=["Properties"])
def create_property(property_data: Property):
    """Add a new property listing to the system."""
    db_properties[property_data.id] = property_data
    return property_data


# --- LEADS ENDPOINTS ---

@app.post("/leads", response_model=Lead, status_code=status.HTTP_201_CREATED, tags=["Leads"])
def capture_lead(lead_data: Lead):
    """Capture info from an interested client (Ava's core capability)."""
    db_leads[lead_data.id] = lead_data
    return lead_data

@app.get("/leads", response_model=List[Lead], tags=["Leads"])
def get_leads():
    """Get a list of all registered leads."""
    return list(db_leads.values())


# --- APPOINTMENTS ENDPOINTS ---

@app.post("/appointments", response_model=Appointment, status_code=status.HTTP_201_CREATED, tags=["Appointments"])
def book_appointment(booking: AppointmentCreate):
    """Book a new property tour or consultation."""
    # Enforce data consistency: check if lead and property exist
    if booking.lead_id not in db_leads:
        raise HTTPException(status_code=404, detail="Lead profile not found. Register the lead first.")
    
    if booking.property_id not in db_properties:
        raise HTTPException(status_code=404, detail="Property listing not found.")
    
    # Create the complete appointment object
    appointment = Appointment(
        lead_id=booking.lead_id,
        property_id=booking.property_id,
        appointment_time=booking.appointment_time,
        notes=booking.notes
    )
    db_appointments[appointment.id] = appointment
    return appointment

@app.get("/appointments", response_model=List[Appointment], tags=["Appointments"])
def list_appointments():
    """Retrieve all scheduled viewings."""
    return list(db_appointments.values())

@app.patch("/appointments/{appointment_id}/cancel", response_model=Appointment, tags=["Appointments"])
def cancel_appointment(appointment_id: UUID):
    """Cancel a scheduled appointment."""
    if appointment_id not in db_appointments:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    
    db_appointments[appointment_id].status = "Cancelled"
    return db_appointments[appointment_id]