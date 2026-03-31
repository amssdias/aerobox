from dataclasses import dataclass
from typing import Optional


@dataclass
class CheckoutSessionInfo:
    id: str
    status: Optional[str]
    payment_status: Optional[str]
    mode: Optional[str]
    customer_email: Optional[str]
    amount_total: Optional[int]
    currency: Optional[str]
    created: Optional[int]
