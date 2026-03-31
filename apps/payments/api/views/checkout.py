from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.integrations.stripe.payments.exceptions import StripeCheckoutSessionNotFoundError, StripeCheckoutSessionError
from apps.payments.api.serializers import CheckoutSessionQuerySerializer, CheckoutSessionInfoSerializer
from apps.payments.domain.exceptions import CheckoutSessionPermissionDeniedError
from apps.payments.services.stripe_api import get_stripe_session_info
from apps.subscriptions.api.serializers import CheckoutSubscriptionSerializer


@extend_schema(tags=["API - Payments"])
class CheckoutSessionViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CheckoutSubscriptionSerializer

    @action(detail=False, methods=["post"], url_path="session")
    def create_checkout(self, request):
        """
        Creates a Stripe checkout session URL for the user to complete their payment.

        This endpoint generates a checkout session, allowing the user to proceed with
        the payment for their subscription.
        """

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            data = serializer.get_checkout_session_url(user=request.user)
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], url_path="session/info")
    def get_session_info(self, request, *args, **kwargs):
        serializer = CheckoutSessionQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data["session_id"]

        try:
            session_info = get_stripe_session_info(session_id, self.request.user)
        except StripeCheckoutSessionNotFoundError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except StripeCheckoutSessionError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except CheckoutSessionPermissionDeniedError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )

        output_serializer = CheckoutSessionInfoSerializer(session_info)
        return Response(output_serializer.data, status=status.HTTP_200_OK)
