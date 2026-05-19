import requests
from typing import Optional
from livekit.agents import function_tool, RunContext

BASE_URL = "http://127.0.0.1:8000"

class RealEstateCRMTools:
    """
    A container class matching LiveKit 1.0 standards.
    This explicitly exposes the functions agent.py wants to import.
    """

    @function_tool(
        description="Retrieves all available real estate property listings from the CRM database. Call this when the user asks what properties, houses, or apartments are available."
    )
    def get_available_properties(self, ctx: RunContext) -> str:
        try:
            response = requests.get(f"{BASE_URL}/properties")
            if response.status_code == 200:
                return str(response.json())
            return f"Error: Unable to fetch properties (Status {response.status_code})"
        except requests.exceptions.ConnectionError:
            return "Error: CRM backend server is currently offline."

    @function_tool(
        description="Registers or captures a new client lead in the CRM. Must be used when the user provides their profile details or before booking an appointment."
    )
    def capture_client_lead(self, ctx: RunContext, name: str, email: str, phone: str, budget: float) -> str:
        payload = {"name": name, "email": email, "phone": phone, "budget": budget}
        try:
            response = requests.post(f"{BASE_URL}/leads", json=payload)
            return str(response.json())
        except Exception as e:
            return f"Error capturing lead: {str(e)}"

    @function_tool(
        description="Schedules a property viewing appointment or site tour inside the CRM. Requires a valid lead_id and property_id."
    )
    def book_viewing_appointment(self, ctx: RunContext, lead_id: str, property_id: str, appointment_time: str, notes: Optional[str] = None) -> str:
        payload = {
            "lead_id": lead_id,
            "property_id": property_id,
            "appointment_time": appointment_time,
            "notes": notes
        }
        try:
            response = requests.post(f"{BASE_URL}/appointments", json=payload)
            return str(response.json())
        except Exception as e:
            return f"Error booking appointment: {str(e)}"