from enum import StrEnum


class PeoplePageState(StrEnum):
    READY = "READY"
    NO_RESULTS = "NO_RESULTS"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    CAPTCHA = "CAPTCHA"
    ACCESS_RESTRICTED = "ACCESS_RESTRICTED"
    UNEXPECTED_PAGE = "UNEXPECTED_PAGE"
    TIMEOUT = "TIMEOUT"
    SELECTOR_MISMATCH = "SELECTOR_MISMATCH"


class PeopleSearchAccessError(RuntimeError):
    def __init__(self, state: PeoplePageState, message: str) -> None:
        super().__init__(message)
        self.state = state