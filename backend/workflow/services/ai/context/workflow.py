class WorkflowContextBuilder:

    @classmethod
    def build(
        cls,
        instance,
    ):

        return {
            "workflow": instance.workflow.name,
            "workflow_id": str(instance.workflow.id),
            "organization": instance.organization.name,
            "variables": instance.context or {},
        }