from django_filters import rest_framework as filters

from apps.cloud_storage.models import Folder


class FolderFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Folder
        fields = ["name"]
