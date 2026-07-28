from uuid import uuid4

from django.contrib.auth import get_user_model

from inbox.models import Organization
from workflow.models import WorkflowDefinition

User = get_user_model()


def create_test_user():
    return User.objects.create_user(
        email=f"{uuid4()}@workflow.test",
        password="password123",
    )


def create_test_organization():
    uid = uuid4().hex[:8]

    return Organization.objects.create(
        name=f"Workflow Org {uid}",
        slug=f"workflow-org-{uid}",
    )


def create_workflow():

    organization = create_test_organization()
    user = create_test_user()

    return WorkflowDefinition.objects.create(
        organization=organization,
        name="Approval Workflow",
        code=f"WF_{uuid4().hex[:8].upper()}",
        created_by=user,
    )