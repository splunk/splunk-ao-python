from enum import Enum


class ViolationReason(str, Enum):
    ADVISORY = "advisory"
    END_OF_LIFE = "end_of_life"
    NOT_ALLOWED = "not_allowed"
    SECURITY_DECISION = "security_decision"
    YANKED = "yanked"

    def __str__(self) -> str:
        return str(self.value)
