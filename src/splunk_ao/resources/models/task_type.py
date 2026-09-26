from enum import IntEnum


class TaskType(IntEnum):
    VALUE_13 = 13
    VALUE_15 = 15
    VALUE_16 = 16
    VALUE_17 = 17
    VALUE_18 = 18

    def __str__(self) -> str:
        return str(self.value)
