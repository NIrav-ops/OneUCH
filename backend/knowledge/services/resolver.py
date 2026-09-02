from knowledge.models import BusinessIdentity
from context.models import (
    BusinessObject,
    BusinessObjectAlias,
    BusinessObjectDomain,
)

from knowledge.services.logger import log_info

from knowledge.services.identity_normalizer import (
    IdentityNormalizer,
)
from context.services.business_object_cache import (
    BusinessObjectCache,
)


class BusinessObjectResolver:

    @staticmethod
    def resolve(
        *,
        organization,
        sender="",
        subject="",
        body="",
    ):

        candidates = []

        sender = sender or ""
        subject = subject or ""
        body = body or ""

        sender_lower = sender.lower()
        subject_lower = subject.lower()
        body_lower = body.lower()

        business_objects = (
            BusinessObjectCache.get_objects(
                organization
            )
        )

        for obj in business_objects:

            confidence = 0

            reasons = []

            # -----------------------------
            # Rule 1
            # Identity Match
            # -----------------------------

            identities = BusinessIdentity.objects.filter(
                business_object=obj,
            )

            for identity in identities:

                value = identity.normalized_value

                if identity.identity_type == "EMAIL":

                    if value == IdentityNormalizer.normalize(
                        "EMAIL",
                        sender,
                    ):

                        confidence += 100

                        reasons.append(
                            f"Matched email identity ({value})"
                        )

                elif identity.identity_type == "DOMAIN":

                    normalized_domain = IdentityNormalizer.normalize(
                        "DOMAIN",
                        sender.split("@")[-1]
                        if "@" in sender
                        else sender,
                    )

                    if value == normalized_domain:

                        confidence += 90

                        reasons.append(
                            f"Matched sender domain ({value})"
                        )

                elif identity.identity_type == "ALIAS":

                    if value in subject_lower:

                        confidence += 40

                        reasons.append(
                            f"Matched alias in subject ({value})"
                        )

                    if value in body_lower:

                        confidence += 20

                        reasons.append(
                            f"Matched alias in body ({value})"
                        )

            # -----------------------------
            # Rule 2
            # Legacy Alias
            # -----------------------------

            aliases = BusinessObjectAlias.objects.filter(
                business_object=obj,
            )

            for alias in aliases:

                alias_name = alias.alias.lower()

                if alias_name in subject_lower:

                    confidence += 30

                    reasons.append(
                        f"Matched legacy alias ({alias.alias})"
                    )

            # -----------------------------
            # Rule 3
            # Legacy Domain
            # -----------------------------

            domains = BusinessObjectDomain.objects.filter(
                business_object=obj,
            )

            sender_domain = ""

            if "@" in sender:

                sender_domain = sender.split("@")[-1].lower()

            for domain in domains:

                if domain.domain.lower() == sender_domain:

                    confidence += 70

                    reasons.append(
                        f"Matched legacy domain ({domain.domain})"
                    )

            if confidence > 0:

                candidates.append(
                    {
                        "business_object": obj,

                        # Keep the unbounded scoring value only
                        # for deterministic candidate ranking.
                        "resolution_score": confidence,

                        # Public/persisted confidence is always
                        # bounded to the Knowledge contract.
                        "confidence": min(
                            confidence,
                            100,
                        ),

                        "reasons": reasons,
                    }
                )

        candidates.sort(
            key=lambda x: (
                x.get(
                    "resolution_score",
                    x["confidence"],
                )
            ),
            reverse=True,
        )

        if candidates:

            log_info(
                "BusinessObject resolved",
                business_object=candidates[0]["business_object"].id,
                confidence=candidates[0]["confidence"],
            )

            best_match = candidates[0]

            related_objects = [
                candidate["business_object"]
                for candidate in candidates
            ]

            return {
                "matched": True,
                "best_match": best_match,
                "candidates": candidates,
                "related_objects": related_objects,
            }

        log_info(
            "BusinessObject resolution failed"
        )

        return {
            "matched": False,
            "best_match": None,
            "candidates": [],
            "related_objects": [],
        }
