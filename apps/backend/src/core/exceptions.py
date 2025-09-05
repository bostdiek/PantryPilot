class DomainError(Exception):
    """Base class for domain-specific errors."""

    pass


class DuplicateUserError(DomainError):
    """Exception raised when attempting to create a user that already exists."""

    pass


class UserNotFoundError(DomainError):
    """Exception raised when a user is not found in the database."""

    pass
