"""
Enterprise AI Context Builder.

Builds a normalized, provider-independent, JSON-safe context
for AI execution.

This layer intentionally does not call any AI provider.
Its responsibility is only context construction.
"""

from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


class AIContextBuilder:

    CONTEXT_VERSION = "1.0"

    @classmethod
    def build(
        cls,
        workflow_instance=None,
        business_object=None,
        runtime_context=None,
    ) -> dict:
        """
        Build normalized enterprise context.

        All returned values must be safe for:
        - JSON serialization
        - prompt rendering
        - audit logging
        - provider requests
        """

        context = {
            "context_version":
                cls.CONTEXT_VERSION,

            "workflow":
                cls._build_workflow_context(
                    workflow_instance
                ),

            "organization":
                cls._build_organization_context(
                    workflow_instance
                ),

            "actor":
                cls._build_actor_context(
                    workflow_instance
                ),

            "business_object":
                cls._build_business_object_context(
                    business_object
                ),

            "runtime":
                cls._build_runtime_context(
                    runtime_context
                ),
        }

        return cls._make_json_safe(
            context
        )

    # ---------------------------------------------------------
    # Workflow
    # ---------------------------------------------------------

    @classmethod
    def _build_workflow_context(
        cls,
        instance,
    ):

        if instance is None:
            return None

        workflow = getattr(
            instance,
            "workflow",
            None,
        )

        return {
            "instance_id": cls._stringify(
                getattr(
                    instance,
                    "id",
                    None,
                )
            ),
            "status": getattr(
                instance,
                "status",
                None,
            ),
            "workflow_id": cls._stringify(
                getattr(
                    instance,
                    "workflow_id",
                    None,
                )
            ),
            "workflow_name": getattr(
                workflow,
                "name",
                None,
            ),
        }

    # ---------------------------------------------------------
    # Organization / tenant boundary
    # ---------------------------------------------------------

    @classmethod
    def _build_organization_context(
        cls,
        instance,
    ):

        if instance is None:
            return None

        organization = getattr(
            instance,
            "organization",
            None,
        )

        if organization is None:
            return None

        return {
            "id": cls._stringify(
                getattr(
                    organization,
                    "id",
                    None,
                )
            ),
            "name": getattr(
                organization,
                "name",
                None,
            ),
            "slug": getattr(
                organization,
                "slug",
                None,
            ),
        }

    # ---------------------------------------------------------
    # Actor
    # ---------------------------------------------------------

    @classmethod
    def _build_actor_context(
        cls,
        instance,
    ):

        if instance is None:
            return None

        actor = getattr(
            instance,
            "started_by",
            None,
        )

        if actor is None:
            return None

        return {
            "id": cls._stringify(
                getattr(
                    actor,
                    "id",
                    None,
                )
            ),
            "email": getattr(
                actor,
                "email",
                None,
            ),
            "role": getattr(
                actor,
                "role",
                None,
            ),
        }

    # ---------------------------------------------------------
    # Business Object
    # ---------------------------------------------------------

    @classmethod
    def _build_business_object_context(
        cls,
        business_object,
    ):

        if business_object is None:
            return None

        # Support dictionaries because runtime context may already
        # contain a normalized business-object representation.
        if isinstance(
            business_object,
            dict,
        ):
            return deepcopy(
                business_object
            )

        object_type = getattr(
            business_object,
            "object_type",
            None,
        )

        object_type_name = None

        if object_type is not None:

            object_type_name = (
                getattr(
                    object_type,
                    "name",
                    None,
                )
                or getattr(
                    object_type,
                    "key",
                    None,
                )
                or str(object_type)
            )

        return {
            "id": cls._stringify(
                getattr(
                    business_object,
                    "id",
                    None,
                )
            ),
            "type": object_type_name,
            "status": getattr(
                business_object,
                "status",
                None,
            ),
        }

    # ---------------------------------------------------------
    # Runtime context
    # ---------------------------------------------------------

    @classmethod
    def _build_runtime_context(
        cls,
        runtime_context,
    ):

        if runtime_context is None:
            return {}

        if hasattr(
            runtime_context,
            "serialize",
        ):
            runtime_context = (
                runtime_context.serialize()
            )

        if not isinstance(
            runtime_context,
            dict,
        ):
            return {}

        return deepcopy(
            runtime_context
        )

    # ---------------------------------------------------------
    # Serialization safety
    # ---------------------------------------------------------

    @classmethod
    def _make_json_safe(
        cls,
        value,
    ):
        """
        Recursively normalize values into JSON-safe structures.

        This prevents UUID/date/Decimal/model-like values from
        leaking directly into provider payloads.
        """

        if value is None:
            return None

        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value

        if isinstance(
            value,
            UUID,
        ):
            return str(value)

        if isinstance(
            value,
            (
                datetime,
                date,
            ),
        ):
            return value.isoformat()

        if isinstance(
            value,
            Decimal,
        ):
            return str(value)

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key):
                    cls._make_json_safe(
                        item
                    )
                for key, item
                in value.items()
            }

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            return [
                cls._make_json_safe(
                    item
                )
                for item in value
            ]

        # We deliberately do not serialize an arbitrary Django
        # model's entire __dict__, because that could expose
        # fields that were never intended for an AI provider.

        return str(value)

    @staticmethod
    def _stringify(
        value,
    ):

        if value is None:
            return None

        return str(value)