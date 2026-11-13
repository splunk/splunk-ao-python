from enum import Enum


class LunaSemanticMappingTargetField(str, Enum):
    DOCUMENTS = "documents"
    EVALUATOR_GROUND_TRUTH = "evaluator_ground_truth"
    GENERATED_OUTPUT = "generated_output"
    GROUND_TRUTH = "ground_truth"
    INPUT = "input"
    LABEL = "label"
    METADATA = "metadata"
    OUTPUT = "output"
    TOOLS = "tools"

    def __str__(self) -> str:
        return str(self.value)
