from config.exceptions import DomainError


class FolderError(DomainError):
    default_message = "A folder error occurred."
    default_code = "folder_error"


class FolderContainsFilesOrSubfoldersError(FolderError):
    default_message = "Folder contains files or subfolders."
    default_code = "folder_with_content_inside"
