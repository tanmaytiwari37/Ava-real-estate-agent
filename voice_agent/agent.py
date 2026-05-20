import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, room_io
from livekit.plugins import noise_cancellation, silero
from tools import RealEstateCRMTools

current_dir = os.path.dirname(__file__)
load_dotenv(os.path.join(current_dir, ".env"), override=True)

vad = silero.VAD.load()
crm_tools = RealEstateCRMTools()
server = AgentServer()

class Ava(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                # === Identity ===
                "You are Ava, a warm and professional real estate voice assistant. "
                "You help users buy or rent properties.\n\n"

                "VOICE RULES:\n"
                "- Speak in 1-2 sentences. Never long paragraphs.\n"
                "- Ask exactly ONE question per turn. Never stack questions.\n"
                "- Use natural conversational language, not formal phrases.\n"
                "- Never use bullet points or lists — they don't work in speech.\n\n"

                "DISCOVERY WORKFLOW:\n"
                "When a user shows interest in a property, gather these details "
                "ONE AT A TIME in this order:\n"
                "1. Buy or rent?\n"
                "2. Preferred city or area\n"
                "3. Property type (apartment, villa, plot, commercial)\n"
                "4. Bedrooms / BHK\n"
                "5. Budget range\n"
                "6. Timeline (immediate, 3 months, exploring)\n\n"

                "Skip a question if the user already mentioned that detail. "
                "After all 6 are gathered, summarize back what you understood and "
                "confirm before recommending properties.\n\n"

                "BEHAVIOR:\n"
                "- If the user is vague, ask a gentle clarifying question.\n"
                "- If they sound rushed, keep your replies even shorter.\n"
                "- If they go off-topic, politely return to real estate.\n"
                "- Never invent property names, prices, or availability.\n"
                "- Never give legal or financial guarantees.\n\n"

                "CLOSING:\n"
                "When the user is ready to act, offer to schedule a site visit "
                "or connect them with a human agent."
            ),
            tools=[
                crm_tools.get_available_properties,
                crm_tools.capture_client_lead,
                crm_tools.book_viewing_appointment,
            ],
        )

async def warm_backend():
    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get("https://ava-p7m1.onrender.com/properties", timeout=5) as resp:
                await resp.text()
    except Exception:
        pass

@server.rtc_session()
async def entrypoint(ctx: JobContext):
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

if __name__ == "__main__":
    agents.cli.run_app(server)