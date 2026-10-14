import base64
import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings

from .base import (
    PaymentProvider,
    PaymentProviderError,
    PaymentProviderRequest,
    PaymentProviderResult,
    PaymentProviderStatus,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MpesaConfig:
    enabled: bool
    environment: str
    base_url: str
    api_key: str
    public_key: str
    service_provider_code: str
    market: str = "vodacomTZN"
    country: str = "TZN"
    currency: str = "TZS"
    c2b_path: str = "ipg/v2/{market}/c2bPayment/singleStage/"
    query_path: str = "ipg/v2/{market}/queryTransactionStatus/"
    timeout_seconds: float = 20.0

    @classmethod
    def from_django_settings(cls):
        values = settings.MPESA
        return cls(**values)

    @property
    def configured(self):
        return bool(
            self.enabled
            and self.base_url
            and self.api_key
            and self.public_key
            and self.service_provider_code
        )


class JsonHttpTransport:
    def post(self, url, *, headers, payload, timeout):
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except HTTPError as error:
            error.read()
            logger.warning(
                "M-Pesa returned HTTP %s for %s",
                error.code,
                url,
            )
            raise PaymentProviderError(
                "MPESA_HTTP_ERROR",
                "M-Pesa rejected the payment request.",
                retryable=error.code >= 500,
                status_code=error.code,
            ) from error
        except (TimeoutError, URLError) as error:
            logger.warning("M-Pesa request failed for %s: %s", url, type(error).__name__)
            raise PaymentProviderError(
                "MPESA_UNAVAILABLE",
                "M-Pesa could not be reached. Try again shortly.",
                retryable=True,
            ) from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PaymentProviderError(
                "MPESA_INVALID_RESPONSE",
                "M-Pesa returned an invalid response.",
                retryable=True,
            ) from error


class MpesaProvider(PaymentProvider):
    key = "vodacom_m_pesa"
    display_name = "Vodacom M-Pesa"

    def __init__(self, config=None, transport=None):
        self.config = config or MpesaConfig.from_django_settings()
        self.transport = transport or JsonHttpTransport()

    @property
    def configured(self):
        return self.config.configured

    def initiate(self, payment):
        self._require_configured()
        self._validate_payment(payment)
        payload = {
            "input_Amount": self._amount(payment.amount),
            "input_Country": self.config.country,
            "input_Currency": self.config.currency,
            "input_CustomerMSISDN": self._msisdn(payment.payer_phone_number),
            "input_ServiceProviderCode": self.config.service_provider_code,
            "input_ThirdPartyConversationID": payment.conversation_id,
            "input_TransactionReference": payment.reference,
            "input_PurchasedItemsDesc": payment.description[:100],
        }
        response = self._post(self.config.c2b_path, payload)
        return self._result(response, initiation=True)

    def query(self, payment):
        self._require_configured()
        payload = {
            "input_QueryReference": payment.reference,
            "input_ServiceProviderCode": self.config.service_provider_code,
            "input_ThirdPartyConversationID": payment.conversation_id,
            "input_Country": self.config.country,
        }
        response = self._post(self.config.query_path, payload)
        return self._result(response, initiation=False)

    def _post(self, path, payload):
        endpoint = path.format(market=self.config.market).lstrip("/")
        url = f"{self.config.base_url.rstrip('/')}/{endpoint}"
        return self.transport.post(
            url,
            headers={"Authorization": f"Bearer {self._authorization_token()}"},
            payload=payload,
            timeout=self.config.timeout_seconds,
        )

    def _authorization_token(self):
        try:
            public_key = serialization.load_pem_public_key(
                self.config.public_key.encode("utf-8")
            )
            encrypted_key = public_key.encrypt(
                self.config.api_key.encode("utf-8"),
                padding.PKCS1v15(),
            )
        except (AttributeError, TypeError, ValueError) as error:
            raise PaymentProviderError(
                "MPESA_CONFIGURATION_ERROR",
                "The configured M-Pesa public key is invalid.",
            ) from error
        return base64.b64encode(encrypted_key).decode("ascii")

    def _require_configured(self):
        if not self.config.configured:
            raise PaymentProviderError(
                "MPESA_NOT_CONFIGURED",
                "M-Pesa is not configured.",
            )

    def _validate_payment(self, payment):
        if payment.currency != self.config.currency:
            raise PaymentProviderError(
                "MPESA_CURRENCY_UNSUPPORTED",
                f"M-Pesa only supports {self.config.currency} in this market.",
            )
        if payment.amount <= 0:
            raise PaymentProviderError(
                "MPESA_AMOUNT_INVALID",
                "The payment amount must be greater than zero.",
            )
        self._msisdn(payment.payer_phone_number)

    @staticmethod
    def _amount(amount):
        return format(amount.quantize(Decimal("0.01")), "f")

    @staticmethod
    def _msisdn(phone_number):
        digits = "".join(character for character in phone_number if character.isdigit())
        if digits.startswith("0"):
            digits = f"255{digits[1:]}"
        if not digits.startswith("255") or len(digits) != 12:
            raise PaymentProviderError(
                "MPESA_PHONE_INVALID",
                "Enter a valid Tanzania M-Pesa number.",
            )
        return digits

    @staticmethod
    def _result(response: dict[str, Any], *, initiation):
        response_code = str(response.get("output_ResponseCode", ""))
        transaction_id = response.get("output_TransactionID") or None
        if response_code == "0":
            status = (
                PaymentProviderStatus.PENDING_CUSTOMER_ACTION
                if initiation
                else PaymentProviderStatus.SUCCEEDED
            )
        else:
            status = PaymentProviderStatus.FAILED
        return PaymentProviderResult(
            status=status,
            provider_reference=transaction_id,
            conversation_id=response.get("output_ConversationID") or None,
            transaction_id=transaction_id,
            response_code=response_code or None,
            response_description=response.get("output_ResponseDesc", ""),
            raw_response=response,
        )
