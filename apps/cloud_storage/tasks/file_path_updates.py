from celery import shared_task

from apps.cloud_storage.models import Folder


@shared_task
def update_folder_file_paths_task(folder_id, batch_size=1000):
    folder = Folder.objects.get(id=folder_id)
    folder.update_file_paths(batch_size=batch_size)
