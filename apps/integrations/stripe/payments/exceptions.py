class StripeCheckoutSessionError(Exception):
    pass


class StripeCheckoutSessionNotFoundError(StripeCheckoutSessionError):
    pass
