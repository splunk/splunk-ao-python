from enum import Enum


class ScorerPromptPreviewUnavailableReason(str, Enum):
    AMBIGUOUS_LEGACY_ROLL_UP = "ambiguous_legacy_roll_up"
    ROLL_UP = "roll_up"
    RUN_SETTINGS_UNAVAILABLE = "run_settings_unavailable"
    SCORE_NOT_DIRECTLY_ATTRIBUTABLE = "score_not_directly_attributable"

    def __str__(self) -> str:
        return str(self.value)
