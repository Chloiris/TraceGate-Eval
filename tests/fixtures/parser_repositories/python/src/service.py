from .helper import helper


class BaseService:
    def identity(self, value: int) -> int:
        return value


class Service(BaseService):
    def run(self, value: int) -> int:
        return normalize(helper(value))


def normalize(value: int) -> int:
    return value
