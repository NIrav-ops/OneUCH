import re
from urllib.parse import urlparse


class IdentityNormalizer:

    @staticmethod
    def normalize(identity_type, value):

        if not value:
            return ""

        value = value.strip()

        identity_type = identity_type.upper()

        if identity_type == "EMAIL":
            return value.lower()

        elif identity_type == "DOMAIN":

            value = value.lower()

            value = value.replace("www.", "")

            value = value.replace("http://", "")

            value = value.replace("https://", "")

            value = value.rstrip("/")

            return value

        elif identity_type == "WEBSITE":

            parsed = urlparse(value)

            hostname = parsed.hostname or value

            hostname = hostname.lower()

            hostname = hostname.replace("www.", "")

            return hostname

        elif identity_type == "PHONE":

            return re.sub(r"\D", "", value)

        elif identity_type in [

            "GST",

            "PAN",

            "CRM",

            "ERP",

            "CUSTOMER_ID",

            "VENDOR_ID",

            "EMPLOYEE_ID",

        ]:

            return value.upper()

        elif identity_type == "ALIAS":

            return " ".join(

                value.lower().split()

            )

        return value.lower()