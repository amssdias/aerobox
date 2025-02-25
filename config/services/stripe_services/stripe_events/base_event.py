from abc import ABC, abstractmethod

class StripeEventHandler(ABC):
    """
    Abstract base class for Stripe event handlers.
    """

    def __init__(self, event):
        self.event = event
        self.data = event["data"]["object"]

    @abstractmethod
    def process(self):
        pass
