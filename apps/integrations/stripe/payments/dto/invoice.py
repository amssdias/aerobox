from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional


@dataclass(frozen=True)
class InvoicePaymentSummary:
    """
    Notes:
    - amounts are in the smallest currency unit (e.g. cents)
    - timestamps are UTC datetimes

    https://docs.stripe.com/api/invoices/object?api-version=2025-04-30.basil
    """

    invoice_id: str
    subscription_id: Optional[str]

    payment_method_type: Optional[str]
    amount_paid: Optional[int]
    amount_due: Optional[int]

    paid_at: Optional[datetime]

    hosted_invoice_url: Optional[str]
    invoice_pdf: Optional[str]

    billing_reason: Optional[str]
    subscription_period_end_date: Optional[date]
