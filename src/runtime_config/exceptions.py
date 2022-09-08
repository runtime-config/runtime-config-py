class RuntimeConfigBaseException(Exception):
    pass


class InitializationError(RuntimeConfigBaseException):
    pass


class ValidationError(RuntimeConfigBaseException):
    pass
