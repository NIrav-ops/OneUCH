from django.contrib.auth import get_user_model
from django.test import TestCase

from inbox.models import (
    Organization,
    OrganizationUser,
)

from workflow.models import (
    WorkflowDefinition,
    WorkflowInstance,
)

from workflow.services.runtime_governance import (
    WorkflowRuntimeGovernance,
    WorkflowRuntimeGovernanceError,
)


User = get_user_model()


class WorkflowRuntimeGovernanceTests(
    TestCase
):

    def setUp(self):

        self.organization = (
            Organization.objects.create(
                name="Governance Organization",
                slug="governance-organization",
            )
        )

        self.other_organization = (
            Organization.objects.create(
                name="Other Governance Organization",
                slug="other-governance-organization",
            )
        )

        self.member = User.objects.create_user(
            email="member@example.com",
            password="test-password",
        )

        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="test-password",
        )

        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="test-password",
        )

        self.other_member = User.objects.create_user(
            email="other@example.com",
            password="test-password",
        )

        OrganizationUser.objects.create(
            user=self.member,
            organization=self.organization,
            role="member",
        )

        OrganizationUser.objects.create(
            user=self.admin,
            organization=self.organization,
            role="admin",
        )

        OrganizationUser.objects.create(
            user=self.owner,
            organization=self.organization,
            role="owner",
        )

        OrganizationUser.objects.create(
            user=self.other_member,
            organization=self.other_organization,
            role="member",
        )

        self.workflow = (
            WorkflowDefinition.objects.create(
                organization=self.organization,
                name="Governance Workflow",
                code="GOVERNANCE_WORKFLOW",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        self.instance = (
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                organization=self.organization,
                started_by=self.member,
                context={},
            )
        )

        self.other_workflow = (
            WorkflowDefinition.objects.create(
                organization=self.other_organization,
                name="Other Governance Workflow",
                code="OTHER_GOVERNANCE_WORKFLOW",
                version=1,
                status=(
                    WorkflowDefinition.STATUS_ACTIVE
                ),
            )
        )

        self.other_instance = (
            WorkflowInstance.objects.create(
                workflow=self.other_workflow,
                organization=self.other_organization,
                started_by=self.other_member,
                context={},
            )
        )

    def test_member_can_view_own_organization_instance(
        self,
    ):

        result = (
            WorkflowRuntimeGovernance.authorize(
                user=self.member,
                instance=self.instance,
                action=(
                    WorkflowRuntimeGovernance.ACTION_VIEW
                ),
            )
        )

        self.assertTrue(result)

    def test_member_can_control_own_instance(
        self,
    ):

        result = (
            WorkflowRuntimeGovernance.authorize(
                user=self.member,
                instance=self.instance,
                action=(
                    WorkflowRuntimeGovernance.ACTION_RUN
                ),
            )
        )

        self.assertTrue(result)

    def test_member_cannot_control_another_users_instance(
        self,
    ):

        another_user = User.objects.create_user(
            email="another@example.com",
            password="test-password",
        )

        OrganizationUser.objects.create(
            user=another_user,
            organization=self.organization,
            role="member",
        )

        with self.assertRaisesMessage(
            WorkflowRuntimeGovernanceError,
            "You are not authorized to control this workflow execution.",
        ):

            WorkflowRuntimeGovernance.authorize(
                user=another_user,
                instance=self.instance,
                action=(
                    WorkflowRuntimeGovernance.ACTION_CANCEL
                ),
            )

    def test_admin_can_control_any_instance_in_organization(
        self,
    ):

        result = (
            WorkflowRuntimeGovernance.authorize(
                user=self.admin,
                instance=self.instance,
                action=(
                    WorkflowRuntimeGovernance.ACTION_CANCEL
                ),
            )
        )

        self.assertTrue(result)

    def test_owner_can_control_any_instance_in_organization(
        self,
    ):

        result = (
            WorkflowRuntimeGovernance.authorize(
                user=self.owner,
                instance=self.instance,
                action=(
                    WorkflowRuntimeGovernance.ACTION_RESUME
                ),
            )
        )

        self.assertTrue(result)

    def test_cross_organization_access_is_denied(
        self,
    ):

        with self.assertRaisesMessage(
            WorkflowRuntimeGovernanceError,
            "You do not have access to this workflow instance.",
        ):

            WorkflowRuntimeGovernance.authorize(
                user=self.member,
                instance=self.other_instance,
                action=(
                    WorkflowRuntimeGovernance.ACTION_VIEW
                ),
            )

    def test_missing_membership_is_denied(
        self,
    ):

        user = User.objects.create_user(
            email="unassigned@example.com",
            password="test-password",
        )

        with self.assertRaisesMessage(
            WorkflowRuntimeGovernanceError,
            "Authenticated user is not associated with an organization.",
        ):

            WorkflowRuntimeGovernance.authorize(
                user=user,
                instance=self.instance,
                action=(
                    WorkflowRuntimeGovernance.ACTION_VIEW
                ),
            )

    def test_unsupported_action_is_denied(
        self,
    ):

        with self.assertRaisesMessage(
            WorkflowRuntimeGovernanceError,
            "Unsupported runtime governance action.",
        ):

            WorkflowRuntimeGovernance.authorize(
                user=self.member,
                instance=self.instance,
                action="delete",
            )