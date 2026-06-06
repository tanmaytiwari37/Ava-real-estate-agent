import asyncio
import aiohttp
import os
from typing import Optional
from livekit.agents import function_tool, RunContext

BASE_URL = os.environ.get("BACKEND_URL", "https://ava-p7m1.onrender.com")


class RealEstateCRMTools:

    @function_tool(
        description=(
            "Retrieves real estate listings from the CRM filtered by the user's preferences. "
            "Call this after gathering the user's city, budget, bedrooms, and property type. "
            "All parameters are optional — pass only what the user has specified."
        )
    )
    async def get_available_properties(
        self,
        ctx: RunContext,
        city: Optional[str] = None,
        max_price_inr: Optional[float] = None,
        min_bedrooms: Optional[int] = None,
        property_type: Optional[str] = None,
        purpose: Optional[str] = "buy",
    ) -> str:
        # Build query params from whatever the user mentioned
        params = {}
        if city:
            params["city"] = city
        if max_price_inr:
            params["max_price"] = max_price_inr
        if min_bedrooms:
            params["min_bedrooms"] = min_bedrooms
        if property_type:
            params["property_type"] = property_type
        if purpose:
            params["purpose"] = purpose

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{BASE_URL}/properties",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        props = await resp.json()
                        if not props:
                            return (
                                "I couldn't find any properties matching those criteria. "
                                "Would you like to broaden the search, maybe a higher budget or nearby city?"
                            )
                        lines = []
                        for p in props:
                            property_id = p.get("property_id")
                            if purpose.lower() == "rent":
                                rent_val = p.get("monthly_rental_estimate_inr", 0)
                                lines.append(
                                    f"[ID: {property_id}] {p.get('property_type', 'Property')} in {p.get('district', '')}, "
                                    f"{p.get('city', '')}: {p.get('bedrooms', '?')} BHK, "
                                    f"{p.get('built_up_area_sqft', '?')} sqft, "
                                    f"rented at {rent_val:,.0f} rupees per month."
                                )
                            else:
                                price_cr = p.get("price_inr", 0) / 10_000_000
                                lines.append(
                                    f"[ID: {property_id}] {p.get('property_type', 'Property')} in {p.get('district', '')}, "
                                    f"{p.get('city', '')}: {p.get('bedrooms', '?')} BHK, "
                                    f"{p.get('built_up_area_sqft', '?')} sqft, "
                                    f"priced at {price_cr:.1f} crore rupees."
                                )
                        return " ".join(lines)
                    return f"Could not fetch listings. Server returned status {resp.status}."

        except asyncio.TimeoutError:
            return "The property database is taking too long to respond. Please try again shortly."
        except Exception as e:
            return f"Error fetching properties: {str(e)}"

    @function_tool(
        description=(
            "Saves a new client lead into the CRM. "
            "Call this once the user has shared their name and phone. "
            "Email and budget are optional — pass them only if shared."
        )
    )
    async def capture_client_lead(
        self,
        ctx: RunContext,
        name: str,
        phone: str,
        email: Optional[str] = None,
        budget: Optional[float] = None,
    ) -> str:
        payload = {"name": name, "phone": phone}
        if email:
            payload["email"] = email
        if budget:
            payload["budget"] = budget
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BASE_URL}/leads",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    data = await resp.json()
                    if resp.status in (200, 201):
                        lead_id = data.get("id", "unknown")
                        return f"Your details have been saved. Your lead ID is {lead_id}."
                    return f"Failed to save your details. Server said: {data}"
        except Exception as e:
            return f"Error capturing lead: {str(e)}"

    @function_tool(
        description=(
            "Schedules a property viewing appointment in the CRM. "
            "Requires a valid lead_id from capture_client_lead and a property_id from get_available_properties."
        )
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
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    data = await resp.json()
                    if resp.status in (200, 201):
                        return f"Appointment confirmed for {appointment_time}. See you there!"
                    return f"Could not book the appointment. Server responded: {data}"
        except Exception as e:
            return f"Error booking appointment: {str(e)}"