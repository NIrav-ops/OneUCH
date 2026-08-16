from workflow.models import WorkflowInstance


class WorkflowRuntimeGovernanceError(Exception):
    """
    Raised when a user is not allowed to perform
    a runtime operation.
    """

    pass


class WorkflowRuntimeGovernance:

    ACTION_VIEW = "view"
    ACTION_RUN = "run"
    ACTION_RESUME = "resume"
    ACTION_CANCEL = "cancel"

    @staticmethod
    def get_organization(user):

        membership = getattr(
            user,
            "organization_membership",
            None,
        )

        if membership is not None:
            return membership.organization

        organization = getattr(
            user,
            "organization",
            None,
        )

        return organization

    @classmethod
    def authorize(
        cls,
        *,
        user,
        instance: WorkflowInstance,
        action,
    ):
        """
        Authorize a runtime operation against a workflow
        instance.

        This method enforces tenant isolation first and
        then applies action-level governance.
        """

        organization = cls.get_organization(
            user
        )

        if organization is None:

            raise WorkflowRuntimeGovernanceError(
                "Authenticated user is not associated "
                "with an organization."
            )

        if instance.organization_id != organization.pk:

            raise WorkflowRuntimeGovernanceError(
                "You do not have access to this workflow instance."
            )

        if action not in {
            cls.ACTION_VIEW,
            cls.ACTION_RUN,
            cls.ACTION_RESUME,
            cls.ACTION_CANCEL,
        }:

            raise WorkflowRuntimeGovernanceError(
                "Unsupported runtime governance action."
            )

        membership = getattr(
            user,
            "organization_membership",
            None,
        )

        #
        # Organization membership is required for
        # runtime control operations.
        #

        if membership is None:

            raise WorkflowRuntimeGovernanceError(
                "Organization membership is required."
            )

        #
        # Viewing runtime state/history is allowed
        # for organization members.
        #

        if action == cls.ACTION_VIEW:

            return True

        #
        # Organization admins/owners may control
        # any workflow instance belonging to their
        # organization.
        #

        if membership.is_admin():

            return True

        #
        # Non-admin users may control executions
        # they started themselves.
        #

        if instance.started_by_id == user.pk:

            return True

        raise WorkflowRuntimeGovernanceError(
            "You are not authorized to control this "
            "workflow execution."
        )