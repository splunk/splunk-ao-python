from enum import Enum


class CodeMetricPolicyState(str, Enum):
    BLOCKED = "blocked"
    END_OF_LIFE_SOON = "end_of_life_soon"
    SAVE_AGAIN = "save_again"

    def __str__(self) -> str:
        return str(self.value)
