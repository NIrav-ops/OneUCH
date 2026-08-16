import re


class TemplateEngine:

    VARIABLE_PATTERN = re.compile(
        r"\{\{\s*(.*?)\s*\}\}"
    )

    def __init__(self, context):

        self.context = context

    def render(self, value):

        if isinstance(value, str):

            return self._render_string(value)

        if isinstance(value, dict):

            return {
                k: self.render(v)
                for k, v in value.items()
            }

        if isinstance(value, list):

            return [
                self.render(v)
                for v in value
            ]

        return value

    def _render_string(self, value):

        def replace(match):

            variable = match.group(1)

            resolved = self.context.get(variable)

            if resolved is None:
                return match.group(0)

            return str(resolved)

        return self.VARIABLE_PATTERN.sub(
            replace,
            value,
        )