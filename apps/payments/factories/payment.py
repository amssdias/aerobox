import factory

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.models import Payment
from apps.subscriptions.factories.subscription import SubscriptionFactory
from apps.users.factories.user_factory import UserFactory


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    user = factory.SubFactory(UserFactory)
    subscription = factory.SubFactory(SubscriptionFactory)
    status = PaymentStatusChoices.PENDING.value
    stripe_invoice_id = factory.Faker("uuid4")
    invoice_url = factory.Faker("url")
    invoice_pdf_url = factory.Faker("url")
