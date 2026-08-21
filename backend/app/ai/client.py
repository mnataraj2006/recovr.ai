from anthropic import AsyncAnthropic
from app.config.settings import settings

anthropic_client = None

def get_anthropic_client() -> AsyncAnthropic:
    """
    Initializes and returns the shared AsyncAnthropic client.
    Handles dummy keys gracefully for testing environments.
    """
    global anthropic_client
    if anthropic_client is None:
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key or api_key == "mock-key-for-now":
            api_key = "mock_key_placeholder"
        anthropic_client = AsyncAnthropic(api_key=api_key)
    return anthropic_client
