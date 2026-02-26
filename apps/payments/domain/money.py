from decimal import Decimal


def cents_to_euros(cents: int) -> Decimal:
    if cents is None:
        raise ValueError("Cents value cannot be None")
    if cents < 0:
        raise ValueError("Cents value cannot be negative")
    return (Decimal(cents) / Decimal("100")).quantize(Decimal("0.01"))
