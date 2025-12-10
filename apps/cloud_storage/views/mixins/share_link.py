from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.exceptions import NotFound

from apps.cloud_storage.exceptions import Gone
from apps.cloud_storage.models import ShareLink, Folder


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

class ShareLinkAccessMixin:
    """
    Mixin for password-protected share links.

    - build_access_token(share_link): create token after password is OK
    - require_valid_access(request, share_link): ensure header token is valid
    """

    access_header_name = "X-ShareLink-Access"
    access_max_age = 3600  # 1 hour

    # one signer instance, with a specific salt
    signer = TimestampSigner(salt="sharelink-access")

    def build_access_token(self, share_link):
        if not share_link.password:
            return None

        return self.signer.sign(str(share_link.pk))

    def _get_access_token_from_request(self, request):
        return request.headers.get(self.access_header_name)

    def require_valid_access(self, request, share_link):
        if not share_link.password:
            return

        token = self._get_access_token_from_request(request)
        if not token:
            raise AuthenticationFailed(_("Password required for this share link."))

        try:
            pk = self.signer.unsign(token, max_age=self.access_max_age)
        except SignatureExpired:
            raise AuthenticationFailed(_("Access expired, please enter the password again."))
        except BadSignature:
            raise AuthenticationFailed(_("Invalid access token."))

        if str(share_link.pk) != str(pk):
            raise AuthenticationFailed(_("Invalid access token."))
