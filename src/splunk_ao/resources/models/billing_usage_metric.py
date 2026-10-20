from enum import Enum


class BillingUsageMetric(str, Enum):
    LUNA_FINE_TUNING_RUNS = "luna_fine_tuning_runs"
    LUNA_TOKENS = "luna_tokens"
    MONTHLY_ACTIVE_USERS = "monthly_active_users"
    SPANS = "spans"
    TOTAL_USERS = "total_users"
    TRACES = "traces"

    def __str__(self) -> str:
        return str(self.value)
