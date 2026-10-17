"""Resolve configured payment adapters without coupling callers to providers."""

from django.conf import settings

from .airtel import AirtelMoneyProvider
from .base import PaymentProviderError
from .mixx import MixxProvider
from .mock import MockPaymentProvider
from .mpesa import MpesaProvider


def get_payment_provider(provider_key=None):
    """Return the requested adapter or fail before any network call is attempted."""

    selected = provider_key or settings.PAYMENT_PROVIDER
    providers = {
        AirtelMoneyProvider.key: AirtelMoneyProvider,
        MixxProvider.key: MixxProvider,
        MpesaProvider.key: MpesaProvider,
    }
    if settings.PAYMENT_PROVIDER_MODE == "mock" and selected in providers:
        return MockPaymentProvider(
            provider_key=selected,
            scenario_name=settings.PAYMENT_MOCK_SCENARIO,
            fixture_path=settings.PAYMENT_MOCK_FIXTURE,
        )
    provider_class = providers.get(selected)
    if provider_class:
        return provider_class()
    raise PaymentProviderError(
        "PAYMENT_PROVIDER_UNKNOWN",
        f"The payment provider '{selected}' is not supported.",
    )
