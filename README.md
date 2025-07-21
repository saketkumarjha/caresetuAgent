# Business Automation Voice Agent

A LiveKit-based voice agent for customer support and appointment scheduling.

## Setup Instructions

### 1. LiveKit Cloud Account Setup

1. Go to [LiveKit Cloud](https://cloud.livekit.io) and create an account
2. Create a new project for your voice agent
3. Copy your API Key and API Secret from the project settings
4. Update the `.env` file with your credentials

### 2. Required API Keys

You'll need the following API keys:

- LiveKit Cloud API Key and Secret
- AssemblyAI API Key (for speech recognition)
- Google Gemini API Key (for LLM)
- Cartesia API Key (for text-to-speech - primary)
- ElevenLabs API Key (for text-to-speech - fallback, optional)

### 3. Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent
python agent.py
```

## Testing

Use LiveKit Agents Playground for testing:

1. Start the agent locally
2. Connect via the playground interface
3. Test voice conversations

## Telephony Integration

LiveKit provides built-in telephony integration. Configure your phone numbers in the LiveKit Cloud dashboard.
