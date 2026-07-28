class PromptVariables:

    @staticmethod
    def build(**kwargs):

        variables = {}

        for key, value in kwargs.items():

            if value is not None:

                variables[key] = value

        return variables