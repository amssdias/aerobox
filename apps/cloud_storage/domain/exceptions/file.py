from config.exceptions import DomainError


class FileError(DomainError):
    default_message = "File error."
    default_code = "file_error"


class FileNotDeletedError(FileError):
    default_message = "File not deleted."
    default_code = "file_not_deleted"
