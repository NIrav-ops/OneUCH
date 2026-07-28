class KnowledgeContextBuilder:

    @classmethod
    def build(
        cls,
        business_object=None,
    ):

        if business_object is None:
            return {}

        return {
            "business_object": str(
                business_object
            ),
        }