from langchain_core.documents import Document
from typing_extensions import TypedDict


# Define state for application
class State(TypedDict):
    question: str
    context: list[Document]
    answer: str
