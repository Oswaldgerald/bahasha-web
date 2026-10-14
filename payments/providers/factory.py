"""Resolve configured payment adapters without coupling callers to providers."""

from django.conf import settings

from .base import PaymentProviderError
from .mpesa import MpesaProvider


def get_payment_provider(provider_key=None):
    """Return the requested adapter or fail before any network call is attempted."""

    selected = provider_key or settings.PAYMENT_PROVIDER
    if selected == "vodacom_m_pesa":
        return MpesaProvider()
    raise PaymentProviderError(
        "PAYMENT_PROVIDER_UNKNOWN",
        f"The payment provider '{selected}' is not supported.",
    )
