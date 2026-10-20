from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    CAPABILITY_BASED = "capability_based"
    MANAGER = "manager"
    READ_ONLY = "read_only"
    USER = "user"

    def __str__(self) -> str:
        return str(self.value)
