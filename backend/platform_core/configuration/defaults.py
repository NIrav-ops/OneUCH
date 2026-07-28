from platform_core.configuration.manager import (
    ConfigurationManager,
)


def load_defaults():

    ConfigurationManager.set(

        "AI_PROVIDER",

        "OpenAI",

    )

    ConfigurationManager.set(

        "MAX_JOB_RETRIES",

        3,

    )

    ConfigurationManager.set(

        "SCHEDULER_ENABLED",

        True,

    )

    ConfigurationManager.set(

        "NOTIFICATIONS_ENABLED",

        True,

    )

    ConfigurationManager.set(

        "AUDIT_ENABLED",

        True,

    )

    ConfigurationManager.set(

        "WORKFLOW_ENABLED",

        True,

    )