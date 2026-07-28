"""
Enterprise Prompt Catalog.

All AI prompts used by One UCH are defined here.

Templates are provider agnostic.

Business services should NEVER hardcode prompt text.
"""

SYSTEM_PROMPT = """
You are the Enterprise AI engine of One UCH.

Your responsibility is to assist enterprise communication workflows.

Rules:

- Use ONLY the supplied context.
- Never invent facts.
- Clearly indicate when information is insufficient.
- Return structured, deterministic responses.
- Focus on business outcomes.
""".strip()


SUMMARY_PROMPT = {
    "name": "summary",
    "version": "1.0",
    "description": "Enterprise communication summarization",

    "system": SYSTEM_PROMPT,

    "user": """
Summarize the following communication.

{content}
""".strip(),

    "response_type": "summary",

    "required_variables": [
        "content",
    ],

    "metadata": {
        "provider_agnostic": True,
        "temperature": 0.0,
    },
}


CLASSIFICATION_PROMPT = {
    "name": "classification",
    "version": "1.0",
    "description": "Communication classification",

    "system": SYSTEM_PROMPT,

    "user": """
Classify the following communication.

{content}
""".strip(),

    "response_type": "classification",

    "required_variables": [
        "content",
    ],

    "metadata": {
        "provider_agnostic": True,
        "temperature": 0.0,
    },
}


ACTION_EXTRACTION_PROMPT = {
    "name": "action_extraction",
    "version": "1.0",
    "description": "Extract actionable tasks",

    "system": SYSTEM_PROMPT,

    "user": """
Extract every actionable item from the following communication.

{content}
""".strip(),

    "response_type": "action_list",

    "required_variables": [
        "content",
    ],

    "metadata": {
        "provider_agnostic": True,
        "temperature": 0.0,
    },
}