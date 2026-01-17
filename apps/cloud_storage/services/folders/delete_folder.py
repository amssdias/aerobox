from django.db import transaction
from django.db.models import Exists, OuterRef

from apps.cloud_storage.domain.exceptions.folder import (
    FolderContainsFilesOrSubfoldersError,
)
from apps.cloud_storage.models import CloudFile, Folder


def delete_folder(folder_id: int) -> None:
    """
    Deletes folder only if it has no subfolders and no non-deleted files.
    Raises FolderContainsFilesOrSubfoldersError if not empty.
    """

    with transaction.atomic():
        folder = (
            Folder.objects.select_for_update()
            .annotate(
                has_subfolders=Exists(Folder.objects.filter(parent_id=OuterRef("pk"))),
                has_files=Exists(
                    CloudFile.objects.filter(
                        folder_id=OuterRef("pk"), deleted_at__isnull=True
                    )
                ),
            )
            .get(pk=folder_id)
        )

        if folder.has_subfolders or folder.has_files:
            raise FolderContainsFilesOrSubfoldersError()

        folder.delete()
