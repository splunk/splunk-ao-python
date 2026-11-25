from enum import Enum


class ScorerAction(str, Enum):
    AUTOTUNE_APPLY = "autotune_apply"
    CREATE_GLOBAL = "create_global"
    CREATE_SHARED = "create_shared"
    DELETE = "delete"
    EXPORT = "export"
    SHARE = "share"
    UPDATE = "update"

    def __str__(self) -> str:
        return str(self.value)
