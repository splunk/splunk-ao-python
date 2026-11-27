from enum import Enum


class RegisteredScorerValidationStage(str, Enum):
    CHECKING_DEPENDENCIES = "checking_dependencies"
    PREPARING_ENVIRONMENT = "preparing_environment"
    RUNNING_TEST = "running_test"
    SCANNING_CODE = "scanning_code"

    def __str__(self) -> str:
        return str(self.value)
