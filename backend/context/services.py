from context.models import (
    BusinessObject,
    BusinessObjectLink,
)


def link_object(

    business_object,

    instance,

    relationship="related",

):

    return BusinessObjectLink.objects.get_or_create(

        business_object=business_object,

        content_type=instance.__class__.__name__,

        object_id=instance.id,

        defaults={

            "relationship": relationship,

        },

    )


def find_business_object(

    organization,

    subject="",

    body="",

):

    text = f"{subject} {body}".lower()

    objects = BusinessObject.objects.filter(

        organization=organization,

        status="active",

    )

    for obj in objects:

        if obj.name.lower() in text:

            return obj

    return None