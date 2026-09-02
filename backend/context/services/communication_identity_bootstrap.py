from collections import defaultdict

from django.db import transaction

from inbox.models import (
    OrganizationUser,
    RecipientContact,
)

from context.models import (
    BusinessObject,
    BusinessObjectType,
    Person,
)

from context.services.person_resolver import (
    PersonResolver,
)

from knowledge.models import (
    BusinessIdentity,
)


CONSUMER_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "outlook.com",
        "hotmail.com",
        "live.com",
        "msn.com",
        "yahoo.com",
        "yahoo.co.in",
        "icloud.com",
        "me.com",
        "aol.com",
        "proton.me",
        "protonmail.com",
    }
)


MACHINE_LOCAL_PARTS = frozenset(
    {
        "noreply",
        "no-reply",
        "donotreply",
        "do-not-reply",
        "mailer-daemon",
        "postmaster",
        "notifications",
        "notification",
        "alerts",
        "alert",
        "automated",
        "automation",
        "system",
        "support-bot",
    }
)


MACHINE_PREFIXES = (
    "noreply+",
    "no-reply+",
    "notifications+",
    "notification+",
    "alerts+",
)


class CommunicationIdentityBootstrapError(RuntimeError):
    pass


def _organization_for_user(user):
    membership = (
        OrganizationUser.objects
        .select_related("organization")
        .filter(
            user=user,
            organization__is_active=True,
        )
        .first()
    )

    if membership is None:
        raise CommunicationIdentityBootstrapError(
            "Active organization membership required."
        )

    return membership.organization


def _split_email(value):
    normalized = str(value or "").strip().lower()

    if "@" not in normalized:
        return None, None

    local_part, domain = normalized.rsplit("@", 1)

    if not local_part or not domain:
        return None, None

    return local_part, domain


def _is_machine_identity(local_part):
    if not local_part:
        return True

    if local_part in MACHINE_LOCAL_PARTS:
        return True

    for prefix in MACHINE_PREFIXES:
        if local_part.startswith(prefix):
            return True

    return False


def _domain_qualification(stats):
    rule_a = (
        stats["sent"] >= 1
        and stats["messages"] >= 2
    )

    rule_b = (
        stats["human_contacts"] >= 2
        and stats["messages"] >= 5
    )

    rules = []

    if rule_a:
        rules.append("A_SENT_AND_REPEAT")

    if rule_b:
        rules.append("B_MULTI_HUMAN_AND_VOLUME")

    return bool(rules), rules


def build_communication_identity_plan(*, user):
    """
    Build a deterministic, read-only identity bootstrap plan.

    Person:
        Every valid non-machine RecipientContact.

    Company:
        Never auto-create consumer email domains.

        A non-consumer domain qualifies when:

        Rule A:
            sent >= 1
            AND total messages >= 2

        OR

        Rule B:
            human contacts >= 2
            AND total messages >= 5

    All generated business identities remain DISCOVERED.
    """

    organization = _organization_for_user(user)

    contacts = list(
        RecipientContact.objects
        .filter(
            user=user,
            organization=organization,
        )
        .order_by("id")
    )

    human_contacts = []
    machine_contacts = []

    contact_domains = {}

    domain_contacts = defaultdict(list)

    domain_stats = defaultdict(
        lambda: {
            "contacts": 0,
            "human_contacts": 0,
            "machine_contacts": 0,
            "messages": 0,
            "sent": 0,
            "received": 0,
        }
    )

    consumer_domain_contacts = 0

    for contact in contacts:
        local_part, domain = _split_email(
            contact.normalized_email
        )

        if not local_part or not domain:
            continue

        contact_domains[contact.id] = domain

        machine = _is_machine_identity(
            local_part
        )

        if machine:
            machine_contacts.append(contact)
        else:
            human_contacts.append(contact)

        if domain in CONSUMER_DOMAINS:
            consumer_domain_contacts += 1
            continue

        stats = domain_stats[domain]

        stats["contacts"] += 1
        stats["messages"] += int(contact.message_count)
        stats["sent"] += int(contact.sent_count)
        stats["received"] += int(contact.received_count)

        if machine:
            stats["machine_contacts"] += 1
        else:
            stats["human_contacts"] += 1
            domain_contacts[domain].append(contact)

    qualified_domains = set()
    qualification_rules = {}

    for domain, stats in domain_stats.items():
        qualified, rules = _domain_qualification(
            stats
        )

        if not qualified:
            continue

        qualified_domains.add(domain)
        qualification_rules[domain] = rules

    qualified_human_contacts = sum(
        len(domain_contacts[domain])
        for domain in qualified_domains
    )

    return {
        "organization": organization,
        "contacts": contacts,
        "human_contacts": human_contacts,
        "machine_contacts": machine_contacts,
        "contact_domains": contact_domains,
        "domain_contacts": dict(domain_contacts),
        "domain_stats": dict(domain_stats),
        "qualified_domains": qualified_domains,
        "qualification_rules": qualification_rules,
        "summary": {
            "recipient_contacts": len(contacts),
            "human_contacts": len(human_contacts),
            "machine_contacts": len(machine_contacts),
            "consumer_domain_contacts": consumer_domain_contacts,
            "non_consumer_domains": len(domain_stats),
            "qualified_business_domains": len(qualified_domains),
            "qualified_human_contacts": qualified_human_contacts,
        },
    }


def _get_or_create_company_type():
    company_type = (
        BusinessObjectType.objects
        .filter(code="COMPANY")
        .first()
    )

    if company_type is not None:
        return company_type, False

    company_type = (
        BusinessObjectType.objects
        .filter(name__iexact="Company")
        .first()
    )

    if company_type is not None:
        changed_fields = []

        if not company_type.code:
            company_type.code = "COMPANY"
            changed_fields.append("code")

        elif company_type.code != "COMPANY":
            raise CommunicationIdentityBootstrapError(
                "Existing Company type uses incompatible code."
            )

        if not company_type.is_system:
            company_type.is_system = True
            changed_fields.append("is_system")

        if not company_type.is_active:
            company_type.is_active = True
            changed_fields.append("is_active")

        if changed_fields:
            company_type.save(
                update_fields=changed_fields
            )

        return company_type, False

    company_type = BusinessObjectType.objects.create(
        name="Company",
        code="COMPANY",
        is_system=True,
        is_active=True,
    )

    return company_type, True


def _identity_confidence(contact):
    if (
        contact.sent_count > 0
        and contact.received_count > 0
    ):
        return 95

    if contact.sent_count > 0:
        return 85

    if contact.message_count >= 5:
        return 80

    return 70


def _get_business_object_for_domain(
    *,
    organization,
    company_type,
    domain,
    stats,
    rules,
):
    domain_identity = (
        BusinessIdentity.objects
        .select_related("business_object")
        .filter(
            business_object__organization=organization,
            identity_type="DOMAIN",
            normalized_value=domain,
        )
        .first()
    )

    created = False

    if domain_identity is not None:
        business_object = domain_identity.business_object

    else:
        business_object = (
            BusinessObject.objects
            .filter(
                organization=organization,
                object_type=company_type,
                name__iexact=domain,
            )
            .first()
        )

        if business_object is None:
            business_object = BusinessObject.objects.create(
                organization=organization,
                object_type=company_type,
                name=domain,
                description=(
                    "Discovered from governed "
                    "communication history."
                ),
                status="active",
                priority=50,
                metadata={},
            )

            created = True

    bootstrap_metadata = {
        "source": "recipient_directory",
        "lifecycle": "DISCOVERED",
        "domain": domain,
        "contact_count": stats["contacts"],
        "human_contact_count": stats["human_contacts"],
        "machine_contact_count": stats["machine_contacts"],
        "message_count": stats["messages"],
        "sent_count": stats["sent"],
        "received_count": stats["received"],
        "qualification_rules": list(rules),
    }

    metadata = dict(
        business_object.metadata or {}
    )

    if metadata.get("identity_bootstrap") != bootstrap_metadata:
        metadata["identity_bootstrap"] = bootstrap_metadata

        business_object.metadata = metadata

        business_object.save(
            update_fields=[
                "metadata",
                "updated_at",
            ]
        )

    return business_object, created


@transaction.atomic
def bootstrap_communication_identities(*, user):
    """
    Persist deterministic communication identity context.

    Guarantees:
    - tenant scoped
    - idempotent
    - no provider calls
    - no AI
    - no InboxMessage mutation
    - no VERIFIED/TRUSTED auto-promotion
    """

    plan = build_communication_identity_plan(
        user=user
    )

    organization = plan["organization"]

    company_type, type_created = (
        _get_or_create_company_type()
    )

    person_resolver = PersonResolver()

    people_created = 0
    people_updated = 0

    business_objects_created = 0
    domain_identities_created = 0
    email_identities_created = 0

    qualified_domains = (
        plan["qualified_domains"]
    )

    for contact in plan["human_contacts"]:
        domain = (
            plan["contact_domains"].get(
                contact.id
            )
            or ""
        )

        company = (
            domain
            if domain in qualified_domains
            else ""
        )

        existing = (
            Person.objects
            .filter(
                organization=organization,
                email__iexact=contact.normalized_email,
            )
            .first()
        )

        before_name = (
            existing.full_name
            if existing
            else ""
        )

        before_company = (
            existing.company
            if existing
            else ""
        )

        person = person_resolver.resolve(
            organization=organization,
            email=contact.normalized_email,
            full_name=contact.display_name or "",
            company=company,
        )

        if existing is None:
            people_created += 1

        elif (
            person.full_name != before_name
            or person.company != before_company
        ):
            people_updated += 1

    for domain in sorted(
        qualified_domains
    ):
        stats = plan["domain_stats"][domain]

        rules = (
            plan[
                "qualification_rules"
            ][domain]
        )

        business_object, created = (
            _get_business_object_for_domain(
                organization=organization,
                company_type=company_type,
                domain=domain,
                stats=stats,
                rules=rules,
            )
        )

        if created:
            business_objects_created += 1

        _, created = (
            BusinessIdentity.objects
            .get_or_create(
                business_object=business_object,
                identity_type="DOMAIN",
                normalized_value=domain,
                defaults={
                    "value": domain,
                    "source": "discovery",
                    "lifecycle": "DISCOVERED",
                    "confidence_score": 80,
                    "trust_score": 25,
                    "is_primary": True,
                    "metadata": {
                        "discovery_source": "recipient_directory",
                        "message_count": stats["messages"],
                        "human_contact_count": stats["human_contacts"],
                        "qualification_rules": list(rules),
                    },
                },
            )
        )

        if created:
            domain_identities_created += 1

        for contact in (
            plan["domain_contacts"].get(
                domain,
                [],
            )
        ):
            confidence = (
                _identity_confidence(
                    contact
                )
            )

            _, created = (
                BusinessIdentity.objects
                .get_or_create(
                    business_object=business_object,
                    identity_type="EMAIL",
                    normalized_value=contact.normalized_email,
                    defaults={
                        "value": contact.normalized_email,
                        "source": "discovery",
                        "lifecycle": "DISCOVERED",
                        "confidence_score": confidence,
                        "trust_score": 25,
                        "is_primary": False,
                        "metadata": {
                            "discovery_source": "recipient_directory",
                            "message_count": contact.message_count,
                            "sent_count": contact.sent_count,
                            "received_count": contact.received_count,
                        },
                    },
                )
            )

            if created:
                email_identities_created += 1

    return {
        "recipient_contacts": plan["summary"]["recipient_contacts"],
        "human_contacts": plan["summary"]["human_contacts"],
        "machine_contacts": plan["summary"]["machine_contacts"],
        "qualified_business_domains": (
            plan["summary"]["qualified_business_domains"]
        ),
        "qualified_human_contacts": (
            plan["summary"]["qualified_human_contacts"]
        ),
        "company_type_created": type_created,
        "people_created": people_created,
        "people_updated": people_updated,
        "business_objects_created": business_objects_created,
        "domain_identities_created": domain_identities_created,
        "email_identities_created": email_identities_created,
        "total_people": (
            Person.objects
            .filter(
                organization=organization
            )
            .count()
        ),
        "total_business_objects": (
            BusinessObject.objects
            .filter(
                organization=organization
            )
            .count()
        ),
        "total_business_identities": (
            BusinessIdentity.objects
            .filter(
                business_object__organization=organization
            )
            .count()
        ),
    }