from ai.services import AIProvider, AIResponse


class SimpleAIProvider(AIProvider):
    """
    Phase-1 safe provider.
    Replace later with OpenAI / Azure / Local LLM.
    """

    def generate(self, prompt: str) -> AIResponse:
        # Placeholder logic (safe for now)
        return AIResponse(
            text="Suggested reply:\n\nThank you for your email. We will review and get back to you shortly."
        )
