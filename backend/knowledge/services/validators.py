"""
Enterprise Knowledge Validators

All incoming data passes through this layer before
being persisted.

Responsibilities

- Required field validation
- Confidence validation
- Metadata validation
- Duplicate safety
- Business rules

Repositories should NEVER validate data.

Services should call validators.
"""

from decimal import Decimal

from .exceptions import (
    InvalidBusinessObject,
    InvalidEvidence,
    InvalidFact,
)


# ==========================================================
# Base Validator
# ==========================================================

class BaseValidator:

    @staticmethod
    def require(value, field_name):

        if value is None:
            raise InvalidEvidence(
                f"{field_name} is required."
            )

        if isinstance(value, str):

            if value.strip() == "":
                raise InvalidEvidence(
                    f"{field_name} is required."
                )

    @staticmethod
    def validate_confidence(confidence):

        if confidence is None:
            return

        value = Decimal(str(confidence))

        if value < 0:
            raise InvalidEvidence(
                "Confidence cannot be negative."
            )

        if value > 100:
            raise InvalidEvidence(
                "Confidence cannot exceed 100."
            )

    @staticmethod
    def validate_metadata(metadata):

        if metadata is None:
            return

        if not isinstance(metadata, dict):
            raise InvalidEvidence(
                "Metadata must be a dictionary."
            )


# ==========================================================
# Business Object
# ==========================================================

class BusinessObjectValidator(BaseValidator):

    @staticmethod
    def validate(business_object):

        if business_object is None:
            raise InvalidBusinessObject(
                "Business Object is required."
            )

        return business_object


# ==========================================================
# Evidence
# ==========================================================

class EvidenceValidator(BaseValidator):

    @classmethod
    def validate(cls, payload):

        cls.require(
            payload.get("organization"),
            "organization",
        )

        cls.require(
            payload.get("message"),
            "message",
        )

        cls.require(
            payload.get("title"),
            "title",
        )

        cls.validate_confidence(
            payload.get("confidence"),
        )

        cls.validate_metadata(
            payload.get("metadata"),
        )

        return payload


# ==========================================================
# Facts
# ==========================================================

class FactValidator(BaseValidator):

    @classmethod
    def validate(cls, payload):

        cls.require(
            payload.get("organization"),
            "organization",
        )

        cls.require(
            payload.get("business_object"),
            "business_object",
        )

        cls.require(
            payload.get("fact_key"),
            "fact_key",
        )

        cls.require(
            payload.get("fact_value"),
            "fact_value",
        )

        cls.validate_confidence(
            payload.get("confidence"),
        )

        cls.validate_metadata(
            payload.get("metadata"),
        )

        return payload


# ==========================================================
# Identity
# ==========================================================

class IdentityValidator(BaseValidator):

    @classmethod
    def validate(cls, payload):

        cls.require(
            payload.get("business_object"),
            "business_object",
        )

        cls.require(
            payload.get("identity_type"),
            "identity_type",
        )

        cls.require(
            payload.get("value"),
            "value",
        )

        cls.validate_metadata(
            payload.get("metadata"),
        )

        return payload