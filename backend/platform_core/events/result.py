from dataclasses import dataclass, field


@dataclass
class EventResult:

    success: bool = True

    errors: list = field(default_factory=list)

    warnings: list = field(default_factory=list)

    metadata: dict = field(default_factory=dict)