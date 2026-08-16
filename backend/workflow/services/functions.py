import json
import uuid

from django.utils import timezone


class BuiltInFunctions:

    @staticmethod
    def uppercase(value):

        if value is None:
            return None

        return str(value).upper()

    @staticmethod
    def lowercase(value):

        if value is None:
            return None

        return str(value).lower()

    @staticmethod
    def title(value):

        if value is None:
            return None

        return str(value).title()

    @staticmethod
    def trim(value):

        if value is None:
            return None

        return str(value).strip()

    @staticmethod
    def concat(*values):

        return "".join(
            str(v)
            for v in values
            if v is not None
        )

    @staticmethod
    def length(value):

        if value is None:
            return 0

        return len(value)

    @staticmethod
    def uuid():

        return str(uuid.uuid4())

    @staticmethod
    def today():

        return timezone.localdate().isoformat()

    @staticmethod
    def now():

        return timezone.now().isoformat()

    @staticmethod
    def json_parse(value):

        return json.loads(value)

    @staticmethod
    def json_stringify(value):

        return json.dumps(value)