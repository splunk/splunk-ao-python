from enum import Enum


class SpanInputSelectionRequestFieldsItem(str, Enum):
    INPUT = "input"
    METADATA = "metadata"
    OUTPUT = "output"

    def __str__(self) -> str:
        return str(self.value)
