class DomainError(Exception):
    """
    Base class for domain-level exceptions.
    """

    default_message = "A domain error occurred."

    def __init__(self, message=None):
        if message is None:
            message = self.default_message
        super().__init__(message)
