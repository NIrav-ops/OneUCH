"""
Enterprise API Versioning

Provides centralized API version
information for the entire platform.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class APIVersion:

    major: int

    minor: int = 0

    patch: int = 0

    @property
    def short(self):

        return f"v{self.major}"

    @property
    def full(self):

        return f"v{self.major}.{self.minor}.{self.patch}"


CURRENT_VERSION = APIVersion(

    major=1,

    minor=0,

    patch=0,

)