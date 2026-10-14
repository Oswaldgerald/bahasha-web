from django.conf import settings

from .base import PaymentProviderError
from .mpesa import MpesaProvider


def get_payment_provider(provider_key=None):
    selected = provider_key or settings.PAYMENT_PROVIDER
    if selected == "vodacom_m_pesa":
        return MpesaProvider()
    raise PaymentProviderError(
        "PAYMENT_PROVIDER_UNKNOWN",
        f"The payment provider '{selected}' is not supported.",
    )
