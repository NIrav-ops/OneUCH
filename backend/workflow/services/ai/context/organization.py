class OrganizationContextBuilder:

    @classmethod
    def build(
        cls,
        organization,
    ):

        return {

            "organization": organization.name,

        }