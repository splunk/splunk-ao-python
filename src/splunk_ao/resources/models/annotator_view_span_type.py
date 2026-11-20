from enum import Enum


class AnnotatorViewSpanType(str, Enum):
    AGENT = "agent"
    CONTROL = "control"
    HTTP = "http"
    LLM = "llm"
    RETRIEVER = "retriever"
    TOOL = "tool"
    WORKFLOW = "workflow"

    def __str__(self) -> str:
        return str(self.value)
