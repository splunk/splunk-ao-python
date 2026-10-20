from enum import Enum


class InsightSummaryLabelType0(str, Enum):
    DECISION = "Decision"
    EFFICIENCY = "Efficiency"
    INSTRUCTION = "Instruction"
    OUTPUT = "Output"
    RELIABILITY = "Reliability"
    RETRIEVAL = "Retrieval"
    SECURITY = "Security"
    TOOL = "Tool"

    def __str__(self) -> str:
        return str(self.value)
