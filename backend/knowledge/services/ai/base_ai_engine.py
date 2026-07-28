"""
Enterprise AI Base Engine

Every future AI provider inherits from this class.

Future Providers

- OpenAI
- Azure OpenAI
- Claude
- Gemini
- Ollama
- Local Models
"""


class BaseAIEngine:

    provider = "base"

    def summarize(
        self,
        text,
    ):
        raise NotImplementedError

    def recommend(
        self,
        context,
    ):
        raise NotImplementedError

    def prioritize(
        self,
        context,
    ):
        raise NotImplementedError

    def detect_risk(
        self,
        context,
    ):
        raise NotImplementedError

    def detect_opportunity(
        self,
        context,
    ):
        raise NotImplementedError