"""
Ava — Real Estate Voice Agent
"""

import logging
import asyncio
import aiohttp
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, room_io
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from tools import RealEstateCRMTools

load_dotenv()

vad = silero.VAD.load()
logger = logging.getLogger(__name__)


class Ava(Agent):
    def __init__(self) -> None:
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
                RealEstateCRMTools().get_available_properties,
                RealEstateCRMTools().capture_client_lead,
                RealEstateCRMTools().book_viewing_appointment,
            ]
        )


server = AgentServer()

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    turn_detector = MultilingualModel(min_endpointing_delay=0.5)

    session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=vad,
        turn_detection=turn_detector,
        preemptive_generation=True,
        allow_fillers=True, 
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

    async def wake_backend():
        try:
            async with aiohttp.ClientSession() as client:
                async with client.get("https://ava-p7m1.onrender.com/properties") as resp:
                    await resp.json()
        except Exception as e:
            logger.error(f"Pre-warm ping failed: {e}")

    asyncio.create_task(wake_backend())

    await session.generate_reply(
        instructions=(
            "Greet the user warmly as Ava. Introduce yourself briefly as a real estate "
            "assistant and ask how you can help today. Keep it under 2 sentences."
        )
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agents.cli.run_app(server)