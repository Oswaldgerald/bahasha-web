"""Mixx by Yas Tanzania collection adapter.

Mixx publishes merchant products publicly, but its technical collection contract
is supplied during merchant onboarding. Endpoint paths are therefore mandatory
configuration and may be changed without touching Bahasha's domain code.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.conf import settings

from .base import (
    PaymentProvider,
    PaymentProviderError,
    PaymentProviderRequest,
    PaymentProviderResult,
    PaymentProviderStatus,
)
from .http import JsonHttpTransport


@dataclass(frozen=True)
class MixxConfig:
    """Immutable Mixx merchant configuration loaded from private settings."""

    enabled: bool
    environment: str
    base_url: str
    client_id: str
    client_secret: str
    merchant_code: str
    token_path: str
    collection_path: str
    query_path: str
    country: str = "TZ"
    currency: str = "TZS"
    timeout_seconds: float = 20.0

    @classmethod
    def from_django_settings(cls):
        """Build immutable adapter configuration from Django settings."""

        return cls(**settings.MIXX)

    @property
    def configured(self):
        """Require the complete onboarding contract before allowing requests."""

        return bool(
            self.enabled
            and self.base_url
            and self.client_id
            and self.client_secret
            and self.merchant_code
            and self.token_path
            and self.collection_path
            and self.query_path
        )


class MixxProvider(PaymentProvider):
    """Translate Bahasha payments to the configured Mixx merchant contract."""

    key = "mixx_by_yas"
    display_name = "Mixx by Yas"

    def __init__(self, config=None, transport=None):
        """Create the adapter with injectable configuration and HTTP transport."""

        self.config = config or MixxConfig.from_django_settings()
        self.transport = transport or JsonHttpTransport("MIXX", self.display_name)

    @property
    def configured(self):
        """Expose whether the approved Mixx contract is fully configured."""

        return self.config.configured

    def initiate(self, payment):
        """Request a Mixx payment prompt using the merchant collection contract."""

        self._require_configured()
        self._validate_payment(payment)
        payload = {
            "merchantCode": self.config.merchant_code,
            "transactionId": payment.conversation_id,
            "reference": payment.reference,
            "amount": self._amount(payment.amount),
            "currency": self.config.currency,
            "country": self.config.country,
            "customer": {"msisdn": self._msisdn(payment.payer_phone_number)},
            "description": payment.description[:100],
        }
        response = self.transport.post(
            self._url(self.config.collection_path),
            headers=self._authorized_headers(),
            payload=payload,
            timeout=self.config.timeout_seconds,
        )
        return self._result(response, initiation=True)

    def query(self, payment):
        """Read the authoritative Mixx state for an existing transaction."""

        self._require_configured()
        path = self.config.query_path.format(
            transaction_id=payment.conversation_id,
            reference=payment.reference,
        )
        response = self.transport.get(
            self._url(path),
            headers=self._authorized_headers(),
            timeout=self.config.timeout_seconds,
        )
        return self._result(response, initiation=False)

    def _authorized_headers(self):
        """Create bearer authorization from server-side Mixx credentials."""

        return {"Authorization": f"Bearer {self._access_token()}"}

    def _access_token(self):
        """Exchange merchant client credentials for a short-lived token."""

        response = self.transport.post(
            self._url(self.config.token_path),
            headers={},
            payload={
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "grant_type": "client_credentials",
            },
            timeout=self.config.timeout_seconds,
        )
        data = response.get("data") or {}
        token = response.get("access_token") or data.get("access_token")
        if not token:
            raise PaymentProviderError(
                "MIXX_AUTHENTICATION_FAILED",
                "Mixx did not provide an access token.",
                retryable=True,
            )
        return token

    def _url(self, path):
        """Join an onboarding-provided endpoint to the Mixx base URL."""

        return f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _require_configured(self):
        """Block calls until every approved Mixx setting is supplied."""

        if not self.config.configured:
            raise PaymentProviderError(
                "MIXX_NOT_CONFIGURED",
                "Mixx by Yas is not configured.",
            )

    def _validate_payment(self, payment):
        """Validate payment details before provider authentication or collection."""

        if payment.currency != self.config.currency:
            raise PaymentProviderError(
                "MIXX_CURRENCY_UNSUPPORTED",
                f"Mixx only supports {self.config.currency} in this market.",
            )
        if payment.amount <= 0:
            raise PaymentProviderError(
                "MIXX_AMOUNT_INVALID",
                "The payment amount must be greater than zero.",
            )
        self._msisdn(payment.payer_phone_number)

    @staticmethod
    def _amount(amount):
        """Format a Mixx transaction amount with two decimal places."""

        return format(amount.quantize(Decimal("0.01")), "f")

    @staticmethod
    def _msisdn(phone_number):
        """Normalize a Tanzanian phone number to twelve provider digits."""

        digits = "".join(character for character in phone_number if character.isdigit())
        if digits.startswith("0"):
            digits = f"255{digits[1:]}"
        if not digits.startswith("255") or len(digits) != 12:
            raise PaymentProviderError(
                "MIXX_PHONE_INVALID",
                "Enter a valid Tanzania Mixx number.",
            )
        return digits

    @staticmethod
    def _result(response: dict[str, Any], *, initiation):
        """Map configured Mixx response fields into stable Bahasha states."""

        data = response.get("data") or {}
        transaction = data.get("transaction") or data
        provider_status = str(
            transaction.get("status") or response.get("status") or ""
        ).upper()
        normalized = {
            "SUCCESS": PaymentProviderStatus.SUCCEEDED,
            "SUCCESSFUL": PaymentProviderStatus.SUCCEEDED,
            "COMPLETED": PaymentProviderStatus.SUCCEEDED,
            "FAILED": PaymentProviderStatus.FAILED,
            "FAILURE": PaymentProviderStatus.FAILED,
            "REJECTED": PaymentProviderStatus.FAILED,
            "PROCESSING": PaymentProviderStatus.PROCESSING,
            "IN_PROGRESS": PaymentProviderStatus.PROCESSING,
        }.get(provider_status)
        if provider_status == "PENDING":
            normalized = (
                PaymentProviderStatus.PENDING_CUSTOMER_ACTION
                if initiation
                else PaymentProviderStatus.PROCESSING
            )
        if normalized is None:
            normalized = (
                PaymentProviderStatus.PENDING_CUSTOMER_ACTION
                if initiation
                else PaymentProviderStatus.PROCESSING
            )
        transaction_id = (
            transaction.get("transactionId")
            or transaction.get("transaction_id")
            or transaction.get("id")
        )
        return PaymentProviderResult(
            status=normalized,
            provider_reference=transaction_id,
            conversation_id=transaction_id,
            transaction_id=transaction_id,
            response_code=str(
                response.get("responseCode") or response.get("code") or ""
            )
            or None,
            response_description=str(
                response.get("message") or transaction.get("message") or ""
            ),
            raw_response=response,
        )
