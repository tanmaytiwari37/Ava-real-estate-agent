"""
Ava — Real Estate Voice Agent
"""

import logging
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
        )



server = AgentServer()

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=vad,
        turn_detection=MultilingualModel(),
        preemptive_generation=True,
        fnc_ctx=RealEstateCRMTools(),
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

    # Make Ava speak first — silence on connect feels broken
    await session.generate_reply(
        instructions=(
            "Greet the user warmly as Ava. Introduce yourself briefly as a real estate "
            "assistant and ask how you can help today. Keep it under 2 sentences."
        )
    )


# ───────────────────────────────────────────────
# SECTION 4: CLI runner
# ───────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agents.cli.run_app(server)
    