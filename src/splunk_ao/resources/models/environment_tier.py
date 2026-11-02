from enum import Enum


class EnvironmentTier(str, Enum):
    CUSTOM = "custom"
    STANDARD = "standard"

    def __str__(self) -> str:
        return str(self.value)
