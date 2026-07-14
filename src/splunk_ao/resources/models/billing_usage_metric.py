from enum import Enum


class BillingUsageMetric(str, Enum):
    LUNA_FINE_TUNING_RUNS = "luna_fine_tuning_runs"
    LUNA_TOKENS = "luna_tokens"
    SPANS = "spans"
    TRACES = "traces"

    def __str__(self) -> str:
        return str(self.value)
