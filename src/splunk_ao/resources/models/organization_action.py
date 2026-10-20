from enum import Enum


class OrganizationAction(str, Enum):
    DELETE = "delete"
    DELETE_LOG_DATA = "delete_log_data"
    READ_AI_USAGE = "read_ai_usage"
    READ_AI_USAGE_ORGANIZATION = "read_ai_usage_organization"
    READ_COST_SETTINGS = "read_cost_settings"
    READ_SETTINGS = "read_settings"
    READ_UNREDACTED_DATA = "read_unredacted_data"
    RENAME = "rename"
    UPDATE_SETTINGS = "update_settings"

    def __str__(self) -> str:
        return str(self.value)
