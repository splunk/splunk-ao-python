from enum import Enum


class ProjectType(str, Enum):
    GEN_AI = "gen_ai"
    PROTECT = "protect"

    def __str__(self) -> str:
        return str(self.value)
