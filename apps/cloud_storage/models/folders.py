from django.conf import settings
from django.db import models

from apps.cloud_storage.models import CloudFile
from config.models.timestampable import Timestampable


class Folder(Timestampable):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="subfolders",
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="folders",
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        unique_together = ("user", "name", "parent")

    def __str__(self):
        return f"{self.name} (ID:{self.id}) - {self.user}"

    def build_path(self):
        parts = []
        current = self

        while current is not None:
            parts.insert(0, current.name)
            current = current.parent

        return "/".join(parts) + "/"

    def get_all_descendant_folders(self):
        descendants = []
        queue = [self]
        while queue:
            current = queue.pop(0)
            children = list(current.subfolders.all())
            descendants.extend(children)
            queue.extend(children)
        return descendants

    def get_all_files_including_nested(self):
        folders = self.get_all_descendant_folders() + [self]
        return CloudFile.objects.filter(folder__in=folders)

    def update_file_paths(self, batch_size=1000):
        files = list(
            self.get_all_files_including_nested().select_related("folder")
        )
        for file in files:
            file.rebuild_path()

        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            CloudFile.objects.bulk_update(batch, ["path"])

    def get_root(self):
        folder = self
        while folder.parent is not None:
            folder = folder.parent
        return folder
