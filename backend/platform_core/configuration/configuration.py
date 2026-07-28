from dataclasses import dataclass


@dataclass
class Configuration:

    key: str

    value: object

    description: str = ""