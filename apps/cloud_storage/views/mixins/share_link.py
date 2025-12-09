from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound

from apps.cloud_storage.exceptions import Gone
from apps.cloud_storage.models import ShareLink


class ShareLinkMixin:
    lookup_url_kwarg = "token"

    def get_object(self):
        token = self.kwargs.get(self.lookup_url_kwarg)
        qs = ShareLink.objects.select_related("owner").prefetch_related(
            "files", "folders"
        )
        try:
            return get_object_or_404(qs, token=token)
        except Http404:
            raise NotFound(_("The link you’re trying to open doesn’t exist."))

    @staticmethod
    def validate_share_link(share_link):
        if share_link.is_revoked:
            raise Gone(_("This link has been disabled by the owner."))

        if share_link.is_expired:
            raise Gone(_("This link has expired and can’t be accessed anymore."))

        return True
