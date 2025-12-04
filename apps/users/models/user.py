from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db.models import Q
from django.utils import timezone

from apps.cloud_storage.exceptions import FolderSharingNotAllowed, ShareLinkLimitReached, ShareLinkExpirationTooLong, \
    ShareLinkPasswordNotAllowed
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices


class User(AbstractUser):

    @property
    def active_subscription(self):
        return (
            self.subscriptions
            .filter(status=SubscriptionStatusChoices.ACTIVE.value)
            .first()
        )

    @property
    def plan(self):
        sub = self.active_subscription
        return sub.plan if sub else None

    @property
    def file_sharing_config(self):
        plan = self.plan
        return plan.file_sharing_config if plan else {}

    @property
    def active_share_links(self):
        return self.share_links.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))

    def validate_create_or_update_sharelink(self, data, create=True):
        file_sharing_config = self.file_sharing_config
        folders = data.get("folders", [])

        if folders and not file_sharing_config.get("allow_folder_sharing", False):
            raise FolderSharingNotAllowed()

        if create:
            max_active_links = file_sharing_config.get("max_active_links", 1)
            active_count = self.active_share_links.count()
            if active_count >= max_active_links:
                raise ShareLinkLimitReached()

        # Expiration handling
        expires_at = data.get("expires_at")
        max_exp_minutes = file_sharing_config.get("max_expiration_minutes",
                                                  settings.DEFAULT_SHARELINK_EXPIRATION_MINUTES)
        now = timezone.now()

        if file_sharing_config.get("allow_choose_expiration", False) and expires_at and max_exp_minutes is not None:
            max_allowed = now + timedelta(minutes=max_exp_minutes)
            if expires_at > max_allowed:
                raise ShareLinkExpirationTooLong()

        raw_password = data.get("password")
        if raw_password and not file_sharing_config.get("allow_password", False):
            raise ShareLinkPasswordNotAllowed()

        return True
