import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, room_io
from livekit.plugins import noise_cancellation, silero
from tools import RealEstateCRMTools

# ── Environment ────────────────────────────────────────────────────────────────
current_dir = os.path.dirname(__file__)
load_dotenv(os.path.join(current_dir, ".env"), override=True)

# ── Shared singletons ──────────────────────────────────────────────────────────
vad = silero.VAD.load()
crm_tools = RealEstateCRMTools()
server = AgentServer()


# ── Agent ──────────────────────────────────────────────────────────────────────
class Ava(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                # === Identity ===
                "You are Ava, a sharp and warm real estate voice assistant for an Indian property CRM. "
                "You help users find, evaluate, and act on property listings — strictly from the live database.\n\n"

                # === Voice Rules ===
                "VOICE RULES:\n"
                "- Speak in 1-2 sentences max. Never long paragraphs.\n"
                "- Ask exactly ONE question per turn. Never stack questions.\n"
                "- Use natural, conversational Indian English — say 'crore' not 'ten million'.\n"
                "- Never use bullet points or lists — they don't work in speech.\n"
                "- Never spell out property IDs or UUIDs to the user.\n\n"

                # === Discovery Workflow ===
                "DISCOVERY WORKFLOW:\n"
                "Gather these details ONE AT A TIME in order:\n"
                "1. Buy or rent?\n"
                "2. Preferred city (available: Bangalore, Mumbai, Chennai, Pune, Hyderabad)\n"
                "3. Property type (apartment, villa, penthouse, independent house, studio)\n"
                "4. Bedrooms / BHK\n"
                "5. Budget range (ask in crores, e.g. 1.5 crore to 3 crore)\n"
                "6. Timeline (immediate, within 3 months, just exploring)\n\n"
                "Skip any question the user already answered. "
                "Once all 6 are gathered, summarize what you understood in one sentence and confirm before calling the database.\n\n"

                # === Database & Property Rules ===
                "DATABASE RULES:\n"
                "- ALWAYS call get_available_properties with the user's filters before mentioning any property.\n"
                "- NEVER invent, assume, or hallucinate property names, prices, areas, or availability.\n"
                "- Only speak about properties that are returned by the tool.\n"
                "- If the tool returns no results, say so honestly and suggest ONE adjustment "
                "(e.g. broader budget, nearby city, or different property type).\n"
                "- If the tool returns results, describe them naturally — mention district, BHK, size, and price in crores.\n"
                "- Cap your spoken list at 3 properties max — offer to narrow further if needed.\n\n"

                # === Lead Capture Rules ===
                "LEAD CAPTURE RULES:\n"
                "- Capture the user's lead (name, email, phone, budget) before booking any appointment.\n"
                "- Ask for contact details naturally: 'May I take your name and number to keep you updated?'\n"
                "- Once lead is saved, confirm it warmly: 'Perfect, I've got your details saved.'\n"
                "- Never ask for Aadhaar, PAN, or any sensitive financial documents.\n\n"

                # === Objection Handling ===
                "OBJECTION HANDLING:\n"
                "- If budget is too low for the city: suggest a nearby area or smaller property type.\n"
                "- If city has no matches: suggest the closest city with available inventory.\n"
                "- If user is comparing options: help them weigh size vs price vs location briefly.\n"
                "- If user is hesitant: acknowledge and ask what their biggest concern is.\n\n"

                # === Behavior ===
                "BEHAVIOR:\n"
                "- If the user is vague, ask one gentle clarifying question.\n"
                "- If they sound rushed, cut replies to one sentence.\n"
                "- If they go off-topic, warmly steer back to real estate.\n"
                "- Never give legal, financial, or investment guarantees.\n"
                "- Never mention internal system errors — say 'I'm having a little trouble, give me a moment' instead.\n\n"

                # === Closing ===
                "CLOSING:\n"
                "When the user is ready to act, offer to book a site visit or connect them with a human agent. "
                "After booking, confirm the appointment details once and close warmly."
            ),
            tools=[
                crm_tools.get_available_properties,
                crm_tools.capture_client_lead,
                crm_tools.book_viewing_appointment,
            ],
        )


# ── Backend warm-up ────────────────────────────────────────────────────────────
async def warm_backend():
    """
    Pings the Render backend on session start to avoid cold-start latency
    during the first real tool call. Silently swallows all errors.
    """
    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(
                "https://ava-p7m1.onrender.com/properties",
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                await resp.text()
    except Exception:
        pass


# ── Session entrypoint ─────────────────────────────────────────────────────────
@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # Fire-and-forget warm-up — doesn't block session start
    asyncio.create_task(warm_backend())

    session = AgentSession(
        stt="deepgram/nova-2",
        llm="openai/gpt-4o-mini",
        tts="cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=vad,
        turn_handling={"endpointing": {"mode": "fixed", "min_delay": 0.3}},
        preemptive_generation=True,
    )

    await session.start(
        agent=Ava(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )

    await session.generate_reply(
        instructions="Briefly greet the user as Ava and ask how you can help."
    )


# ── Entry ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    agents.cli.run_app(server)