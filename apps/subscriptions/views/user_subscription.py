import logging

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.models import Subscription
from apps.subscriptions.serializers.subscription import (
    SubscriptionSerializer,
)

logger = logging.getLogger("aerobox")


@extend_schema(tags=["API - Subscriptions"])
class UserSubscriptionView(RetrieveAPIView):
    serializer_class = SubscriptionSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user

        subscriptions = Subscription.objects.filter(
            user=user,
            status=SubscriptionStatusChoices.ACTIVE.value
        )

        if not subscriptions.exists():
            logger.warning(f"User {user.pk} has no active subscriptions.")
            raise NotFound(detail=_("No active subscription found for the current user."))

        if subscriptions.count() > 1:
            logger.error(f"User {user.pk} has multiple active subscriptions.")
            raise ValidationError(detail=_("Multiple active subscriptions found. Please contact support."))

        return subscriptions.first()
