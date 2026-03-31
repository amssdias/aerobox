from apps.integrations.stripe.payments.dto.checkout_session import CheckoutSessionInfo


def to_checkout_session_summary(session) -> CheckoutSessionInfo:
    customer = session.get("customer")

    return CheckoutSessionInfo(
        id=session.get("id"),
        status=session.get("status"),
        payment_status=session.get("payment_status"),
        mode=session.get("mode"),
        customer_email=(
            customer.get("email")
            if isinstance(customer, dict)
            else session.get("customer_details", {}).get("email")
        ),
        amount_total=session.get("amount_total"),
        currency=session.get("currency"),
        created=session.get("created"),
    )
