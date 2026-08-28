from enum import Enum


class ScorerInvocationPayloadFormat(str, Enum):
    NODE_INPUT_OUTPUT = "node_input_output"
    PAIRWISE = "pairwise"
    QUERY = "query"
    RESPONSE = "response"

    def __str__(self) -> str:
        return str(self.value)
