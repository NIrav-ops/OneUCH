class AIResponse:
    def __init__(self, text: str):
        self.text = text


class AIProvider:
    def generate(self, prompt: str) -> AIResponse:
        raise NotImplementedError("AIProvider.generate() must be implemented")
