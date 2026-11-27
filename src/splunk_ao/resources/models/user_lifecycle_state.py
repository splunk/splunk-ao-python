from enum import Enum


class UserLifecycleState(str, Enum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    REMOVED = "removed"

    def __str__(self) -> str:
        return str(self.value)
