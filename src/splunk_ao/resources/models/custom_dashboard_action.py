from enum import Enum


class CustomDashboardAction(str, Enum):
    DELETE = "delete"
    SHARE = "share"
    TRANSFER = "transfer"
    UPDATE = "update"

    def __str__(self) -> str:
        return str(self.value)
