from enum import Enum


class ModelLifecycleState(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"

    def __str__(self) -> str:
        return str(self.value)
