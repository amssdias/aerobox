from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class SubscriptionSummary:
    subscription_id: str
    customer_id: str
    plan_id: str

    billing_cycle_start: Optional[date]
    billing_cycle_end: Optional[date]
    billing_cycle_interval: Optional[str]
    cancel_at_period_end: Optional[str]
    ended_at: Optional[date]
