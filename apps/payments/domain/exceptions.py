class CheckoutSessionPermissionDeniedError(Exception):
    """Raised when the checkout session does not belong to the authenticated user."""
    pass
