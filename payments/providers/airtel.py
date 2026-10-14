"""Airtel Money Tanzania collection API adapter."""

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
class AirtelMoneyConfig:
    """Immutable Airtel Money configuration loaded from private settings."""

    enabled: bool
    environment: str
    base_url: str
    client_id: str
    client_secret: str
    country: str = "TZ"
    currency: str = "TZS"
    token_path: str = "auth/oauth2/token"
    collection_path: str = "merchant/v1/payments/"
    query_path: str = "standard/v1/payments/{transaction_id}"
    timeout_seconds: float = 20.0

    @classmethod
    def from_django_settings(cls):
        """Build immutable adapter configuration from Django settings."""

        return cls(**settings.AIRTEL_MONEY)

    @property
    def configured(self):
        """Return whether Airtel Money is enabled and credentials are present."""

        return bool(
            self.enabled
            and self.base_url
            and self.client_id
            and self.client_secret
            and self.token_path
            and self.collection_path
            and self.query_path
        )


class AirtelMoneyProvider(PaymentProvider):
    """Translate Bahasha payments to Airtel Money collection operations."""

    key = "airtel_money"
    display_name = "Airtel Money"

    def __init__(self, config=None, transport=None):
        """Create the adapter with injectable configuration and HTTP transport."""

        self.config = config or AirtelMoneyConfig.from_django_settings()
        self.transport = transport or JsonHttpTransport("AIRTEL", self.display_name)

    @property
    def configured(self):
        """Expose whether the selected Airtel environment is ready for calls."""

        return self.config.configured

    def initiate(self, payment):
        """Request an Airtel Money prompt on the member's handset."""

        self._require_configured()
        self._validate_payment(payment)
        payload = {
            "reference": payment.reference,
            "subscriber": {
                "country": self.config.country,
                "currency": self.config.currency,
                "msisdn": self._msisdn(payment.payer_phone_number),
            },
            "transaction": {
                "amount": self._amount(payment.amount),
                "country": self.config.country,
                "currency": self.config.currency,
                "id": payment.conversation_id,
            },
        }
        response = self.transport.post(
            self._url(self.config.collection_path),
            headers=self._authorized_headers(),
            payload=payload,
            timeout=self.config.timeout_seconds,
        )
        return self._result(response, initiation=True)

    def query(self, payment):
        """Ask Airtel Money for the authoritative state of a transaction."""

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
        """Create request headers using a short-lived OAuth access token."""

        return {
            "Authorization": f"Bearer {self._access_token()}",
            "X-Country": self.config.country,
            "X-Currency": self.config.currency,
        }

    def _access_token(self):
        """Exchange server-side client credentials for an Airtel access token."""

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
        token = response.get("access_token")
        if not token:
            raise PaymentProviderError(
                "AIRTEL_AUTHENTICATION_FAILED",
                "Airtel Money did not provide an access token.",
                retryable=True,
            )
        return token

    def _url(self, path):
        """Join a configured relative endpoint to the Airtel base URL."""

        return f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _require_configured(self):
        """Stop before network access when Airtel settings are incomplete."""

        if not self.config.configured:
            raise PaymentProviderError(
                "AIRTEL_NOT_CONFIGURED",
                "Airtel Money is not configured.",
            )

    def _validate_payment(self, payment):
        """Validate the payment before requesting an authentication token."""

        if payment.currency != self.config.currency:
            raise PaymentProviderError(
                "AIRTEL_CURRENCY_UNSUPPORTED",
                f"Airtel Money only supports {self.config.currency} in this market.",
            )
        if payment.amount <= 0:
            raise PaymentProviderError(
                "AIRTEL_AMOUNT_INVALID",
                "The payment amount must be greater than zero.",
            )
        self._msisdn(payment.payer_phone_number)

    @staticmethod
    def _amount(amount):
        """Format an Airtel transaction amount with two decimal places."""

        return format(amount.quantize(Decimal("0.01")), "f")

    @staticmethod
    def _msisdn(phone_number):
        """Normalize a Tanzanian phone number to twelve provider digits."""

        digits = "".join(character for character in phone_number if character.isdigit())
        if digits.startswith("0"):
            digits = f"255{digits[1:]}"
        if not digits.startswith("255") or len(digits) != 12:
            raise PaymentProviderError(
                "AIRTEL_PHONE_INVALID",
                "Enter a valid Tanzania Airtel Money number.",
            )
        return digits

    @staticmethod
    def _result(response: dict[str, Any], *, initiation):
        """Map Airtel response fields into Bahasha's normalized states."""

        data = response.get("data") or {}
        transaction = data.get("transaction") or {}
        status_block = response.get("status") or {}
        provider_status = str(transaction.get("status") or "").upper()
        normalized = {
            "TS": PaymentProviderStatus.SUCCEEDED,
            "SUCCESS": PaymentProviderStatus.SUCCEEDED,
            "SUCCESSFUL": PaymentProviderStatus.SUCCEEDED,
            "TF": PaymentProviderStatus.FAILED,
            "FAILED": PaymentProviderStatus.FAILED,
            "FAILURE": PaymentProviderStatus.FAILED,
            "PROCESSING": PaymentProviderStatus.PROCESSING,
            "AMBIGUOUS": PaymentProviderStatus.PROCESSING,
        }.get(provider_status)
        if provider_status in {"TIP", "PENDING"}:
            normalized = (
                PaymentProviderStatus.PENDING_CUSTOMER_ACTION
                if initiation
                else PaymentProviderStatus.PROCESSING
            )
        if normalized is None:
            normalized = (
                PaymentProviderStatus.PENDING_CUSTOMER_ACTION
                if initiation and status_block.get("success") is True
                else PaymentProviderStatus.PROCESSING
            )
        transaction_id = transaction.get("id") or data.get("transaction_id")
        return PaymentProviderResult(
            status=normalized,
            provider_reference=transaction_id,
            conversation_id=transaction_id,
            transaction_id=transaction_id,
            response_code=str(
                status_block.get("response_code")
                or status_block.get("code")
                or ""
            )
            or None,
            response_description=str(
                transaction.get("message") or status_block.get("message") or ""
            ),
            raw_response=response,
        )
