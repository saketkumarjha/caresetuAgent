"""Clean Simple Voice Agent - No Complex Features."""

import asyncio
import logging
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from livekit.plugins import (
    google,
    elevenlabs, 
    cartesia,
    silero,
    assemblyai,
)

from config import config
from stt_config import create_assemblyai_stt

class Assistant(Agent):
    """Simple assistant agent."""
    
    def __init__(self) -> None:
        super().__init__(instructions="""You are a professional careSetu healthcare voice assistant.

PERSONALITY & TONE:
- Professional, friendly, and helpful
- Patient and understanding with customers
- Clear and concise communication
- Warm but not overly casual

CORE CAPABILITIES:
1. CUSTOMER SUPPORT: Answer questions about careSetu services
2. HEALTHCARE INFORMATION: Provide information about healthcare services
3. APP GUIDANCE: Help users navigate the careSetu app

KNOWLEDGE BASE:
- careSetu offers comprehensive healthcare services including online consultations, lab services, medicine delivery, and home healthcare
- Users can book appointments through the careSetu mobile app available on Play Store and App Store
- For technical support, users can contact sales@akhilsystems.com
- Business hours are typically 9 AM to 6 PM, Monday to Friday
- Emergency services are available 24/7

Remember: You're representing careSetu, so maintain professionalism while being genuinely helpful.""")

class SimpleLLM:
    """Simple LLM wrapper."""
    
    def __init__(self, base_llm):
        self.base_llm = base_llm
        logger.info("✅ Simple LLM wrapper initialized")
    
    async def achat(self, chat_ctx):
        """Simple chat."""
        # Extract user message for logging
        user_text = None
        try:
            if hasattr(chat_ctx, 'messages') and chat_ctx.messages:
                for msg in reversed(chat_ctx.messages):
                    if hasattr(msg, 'role') and msg.role == "user":
                        user_text = msg.content
                        break
        except Exception as e:
            logger.debug(f"Could not extract user message: {e}")
        
        if user_text:
            logger.info(f"👤 User said: {user_text}")
        
        # Return base LLM response directly
        return await self.base_llm.achat(chat_ctx)

async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint."""
    
    logger.info(f"🚀 Starting clean voice agent for room: {ctx.room.name}")
    
    # Verify configuration
    if not config:
        raise ValueError("Configuration not loaded. Please check your .env file.")
    
    # Initialize base LLM
    base_llm = google.LLM(
        model="gemini-1.5-flash",
        api_key=config.google.api_key,
        temperature=0.7,
    )
    
    # Use simple LLM wrapper
    enhanced_llm = SimpleLLM(base_llm)
    
    # Create TTS
    def create_tts():
        if config.cartesia.api_key:
            try:
                return cartesia.TTS(
                    api_key=config.cartesia.api_key,
                    model="sonic-2",
                    voice="f786b574-daa5-4673-aa0c-cbe3e8534c02",
                    language="en",
                )
            except Exception as e:
                logger.warning(f"Cartesia TTS failed: {e}")
        
        if config.elevenlabs.api_key:
            try:
                return elevenlabs.TTS(
                    api_key=config.elevenlabs.api_key,
                    voice="21m00Tcm4TlvDq8ikWAM",
                    model="eleven_turbo_v2",
                )
            except Exception as e:
                logger.warning(f"ElevenLabs TTS failed: {e}")
        
        return google.TTS(voice="en-US-Neural2-F")
    
    # Create AgentSession
    session = AgentSession(
        stt=create_assemblyai_stt(),
        llm=enhanced_llm,
        tts=create_tts(),
        vad=silero.VAD.load(),
    )
    
    # Start the session
    await session.start(
        room=ctx.room,
        agent=Assistant(),
    )
    
    # Connect to the room
    await ctx.connect()
    
    # Generate initial greeting
    try:
        await session.generate_reply(instructions="Greet the user warmly as a careSetu healthcare assistant.")
    except Exception as e:
        logger.warning(f"Greeting failed: {e}")
    
    logger.info("🎤 Clean voice agent ready for conversations")

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))