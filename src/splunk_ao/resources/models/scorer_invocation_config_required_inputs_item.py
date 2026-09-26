from enum import Enum


class ScorerInvocationConfigRequiredInputsItem(str, Enum):
    QUERY = "query"
    RESPONSE = "response"

    def __str__(self) -> str:
        return str(self.value)
