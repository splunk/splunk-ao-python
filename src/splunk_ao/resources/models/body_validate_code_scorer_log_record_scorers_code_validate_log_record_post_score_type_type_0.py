from enum import Enum


class BodyValidateCodeScorerLogRecordScorersCodeValidateLogRecordPostScoreTypeType0(str, Enum):
    BOOL = "bool"
    FLOAT = "float"
    INT = "int"
    STR = "str"

    def __str__(self) -> str:
        return str(self.value)
