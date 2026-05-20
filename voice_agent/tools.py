import asyncio
import aiohttp
from typing import Optional
from livekit.agents import function_tool, RunContext

BASE_URL = "https://ava-p7m1.onrender.com"

class RealEstateCRMTools:

    @function_tool(
        description="Retrieves available real estate listings. Call this when the user asks what properties, houses, or apartments are available."
    )
    async def get_available_properties(self, ctx: RunContext) -> str:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{BASE_URL}/properties", timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        props = await resp.json()
                        if not props:
                            return "There are no properties listed right now."
                        # Format for speech — no bullet points or raw dicts
                        lines = []
                        for p in props[:5]:  # cap at 5 to avoid Ava reading a wall of text
                            lines.append(
                                f"{p.get('title', 'A property')} in {p.get('city', 'an unknown city')}, "
                                f"priced at {p.get('price', 'price not listed')}."
                            )
                        return " ".join(lines)
                    return f"Could not fetch listings. Server returned status {resp.status}."
        except asyncio.TimeoutError:
            return "The property database is taking too long to respond. Please try again shortly."
        except Exception as e:
            return f"Error fetching properties: {str(e)}"

    @function_tool(
        description="Registers a new client lead in the CRM. Use when the user provides their name, email, phone, and budget."
    )
    async def capture_client_lead(
        self, ctx: RunContext, name: str, email: str, phone: str, budget: float
    ) -> str:
        payload = {"name": name, "email": email, "phone": phone, "budget": budget}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BASE_URL}/leads",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    data = await resp.json()
                    if resp.status in (200, 201):
                        lead_id = data.get("id", "unknown")
                        return f"Lead captured successfully. Lead ID is {lead_id}."
                    return f"Failed to save lead. Server said: {data}"
        except Exception as e:
            return f"Error capturing lead: {str(e)}"

    @function_tool(
        description="Schedules a property viewing appointment. Requires a valid lead_id and property_id."
    )
    async def book_viewing_appointment(
        self,
        ctx: RunContext,
        lead_id: str,
        property_id: str,
        appointment_time: str,
        notes: Optional[str] = None,
    ) -> str:
        payload = {
            "lead_id": lead_id,
            "property_id": property_id,
            "appointment_time": appointment_time,
            "notes": notes,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BASE_URL}/appointments",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    data = await resp.json()
                    if resp.status in (200, 201):
                        return f"Appointment booked successfully for {appointment_time}."
                    return f"Could not book appointment. Server responded: {data}"
        except Exception as e:
            return f"Error booking appointment: {str(e)}"