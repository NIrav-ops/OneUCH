"""
Context helper functions.
"""

from platform_core.context.request_store import (
    RequestStore,
)


def get_request_context():

    return RequestStore.get()


def current_user():

    context = RequestStore.get()

    if context:

        return context.user

    return None


def current_organization():

    context = RequestStore.get()

    if context:

        return context.organization

    return None


def current_request_id():

    context = RequestStore.get()

    if context:

        return context.request_id

    return None

def current_tenant():

    context = RequestStore.get()

    if context:

        return context.tenant

    return None

def current_security():

    context = RequestStore.get()

    if context:

        return context.security

    return None


def current_role():

    security = current_security()

    if security:

        return security.role

    return None


def is_admin():

    security = current_security()

    return (
        security.is_superuser
        if security
        else False
    )