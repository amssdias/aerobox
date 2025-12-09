from django.contrib import admin

from apps.cloud_storage.forms.share_link_form import ShareLinkAdminForm
from apps.cloud_storage.models import ShareLink


@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    form = ShareLinkAdminForm
    list_display = (
        "id",
        "owner",
        "revoked_at",
        "expires_at",
        "created_at",
    )
    list_per_page = 25
    readonly_fields = (
        "token",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("owner",)
    filter_horizontal = ("files",)
    autocomplete_fields = ("folders",)
    search_fields = ("token",)
