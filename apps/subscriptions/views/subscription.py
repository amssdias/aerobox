import logging

import stripe
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.utils.size_utils import mb_to_human_gb
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.models import Subscription
from apps.subscriptions.serializers.plan import ChangePlanSerializer

logger = logging.getLogger("aerobox")


@extend_schema(tags=["API - Subscriptions"])
class SubscriptionViewSet(viewsets.GenericViewSet):
    """
    Body: { "target_plan": 3 }
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Subscription.objects.select_related("user")

    def get_object(self):
        obj = super().get_object()

        if obj.user_id != self.request.user.id:
            raise PermissionDenied(_("Not your subscription."))
        return obj

    def get_queryset(self):
        qs = super().get_queryset()

        user = self.request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated(_("Authentication required."))

        qs = qs.filter(user_id=user.id, status=SubscriptionStatusChoices.ACTIVE.value)
        return qs

    @action(detail=True, methods=["post"], url_path="change-plan")
    def change_plan(self, request, pk=None):
        """
        Downgrade
        """
        subscription = self.get_object()

        if subscription.plan.is_free:
            return Response(
                {"detail": _("Can't go lower than this subscription.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ChangePlanSerializer(
            data=request.data, context={"current_plan": subscription.plan}
        )
        serializer.is_valid(raise_exception=True)

        target_plan = serializer.validated_data["target_plan"]

        limit_bytes = target_plan.max_storage_bytes
        limit_str = (
            mb_to_human_gb(limit_bytes)
            if limit_bytes is not None
            else "no enforced limit"
        )

        used_bytes = self._get_user_used_bytes()
        if self._is_over_quota(limit_bytes, used_bytes):
            return Response(
                {"detail": self._get_over_quota_storage_message(used_bytes, limit_str)},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not self.modify_stripe_subscription(subscription, target_plan):
            return Response(
                {
                    "detail": _(
                        "We’re experiencing a temporary issue while updating your subscription. "
                        "Your current plan is still active. Please try again later or contact support if the problem continues."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        plan_label = target_plan.name.get("en")
        plan_message = _(
            "Your subscription is being updated to **{plan}** (storage limit: {limit})."
        ).format(
            plan=plan_label,
            limit=limit_str,
        )
        return Response({"detail": plan_message}, status=status.HTTP_200_OK)

    def _get_user_used_bytes(self) -> int:
        used_bytes = CloudFile.objects.filter(user=self.request.user).aggregate(
            total=Coalesce(Sum("size"), 0)
        )["total"]

        return int(used_bytes or 0)

    @staticmethod
    def _is_over_quota(limit_bytes, used_bytes) -> bool:
        return (limit_bytes is not None) and (used_bytes > limit_bytes)

    @staticmethod
    def _get_over_quota_storage_message(used_bytes, limit_str):
        return _(
            "You're currently using **{used}**, which exceeds your new limit of **{limit}**. "
            "Uploads are temporarily blocked until you delete files or upgrade your plan. "
            "We’ve emailed you details on how to resolve this."
        ).format(
            used=mb_to_human_gb(used_bytes),
            limit=limit_str,
        )

    def modify_stripe_subscription(self, subscription, target_plan):
        try:
            stripe_subscription_id = subscription.stripe_subscription_id
            sub = stripe.Subscription.retrieve(stripe_subscription_id)

            if target_plan.is_free:
                stripe.Subscription.modify(
                    sub.id,
                    cancel_at_period_end=True,
                )
            else:
                item_id = sub["items"]["data"][0]["id"]

                # https://docs.stripe.com/api/subscriptions/update?api-version=2025-06-30.basil
                stripe.Subscription.modify(
                    sub.id,
                    items=[{"id": item_id, "price": target_plan.stripe_price_id}],
                    proration_behavior="create_prorations",
                    billing_cycle_anchor="unchanged",
                    payment_behavior="allow_incomplete",
                )
            return True
        except Exception as e:
            logger.error(
                "Stripe subscription modification failed for user_id=%s, subscription_id=%s, target_plan=%s. Error: %s",
                getattr(self.request.user, "id", None),
                getattr(subscription, "id", None),
                getattr(target_plan, "id", None),
                str(e),
                exc_info=True,
            )
            return False
