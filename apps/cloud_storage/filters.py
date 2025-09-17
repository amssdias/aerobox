from django_filters import rest_framework as filters

from apps.cloud_storage.models import CloudFile


class CloudFileFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="file_name", lookup_expr="icontains")
    no_folder = filters.BooleanFilter(
        field_name="folder",
        lookup_expr="isnull"
    )

    class Meta:
        model = CloudFile
        fields = ["name", "no_folder"]
