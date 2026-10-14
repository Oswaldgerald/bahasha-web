"""Provider-neutral payment contracts used by the Bahasha payment service.

Domain code depends on these types instead of importing an M-Pesa-specific client.
That keeps intent validation and contribution posting reusable for future providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any


class PaymentProviderStatus(StrEnum):
    """Normalized states returned by every external payment provider."""

    PENDING_CUSTOMER_ACTION = "pending_customer_action"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class PaymentProviderRequest:
    """Validated payment data passed from Bahasha to a provider adapter."""

    amount: Decimal
    currency: str
    payer_phone_number: str
    reference: str
    description: str
    conversation_id: str


@dataclass(frozen=True)
class PaymentProviderResult:
    """Provider response translated into Bahasha's normalized state model."""

    status: PaymentProviderStatus
    provider_reference: str | None = None
    conversation_id: str | None = None
    transaction_id: str | None = None
    response_code: str | None = None
    response_description: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict, repr=False)


class PaymentProviderError(Exception):
    """Safe provider failure that may be exposed without leaking credentials."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status_code = status_code


class UnsupportedProviderOperation(PaymentProviderError):
    def __init__(self, operation: str):
        super().__init__(
            "PROVIDER_OPERATION_UNSUPPORTED",
            f"The provider does not support {operation}.",
        )


class PaymentProvider(ABC):
    """Interface implemented by each supported mobile-money provider."""

    key: str
    display_name: str

    @property
    @abstractmethod
    def configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def initiate(self, payment: PaymentProviderRequest) -> PaymentProviderResult:
        raise NotImplementedError

    @abstractmethod
    def query(self, payment: PaymentProviderRequest) -> PaymentProviderResult:
        raise NotImplementedError

    def cancel(self, payment: PaymentProviderRequest) -> PaymentProviderResult:
        """Cancel an unsettled request when the provider supports cancellation."""

        raise UnsupportedProviderOperation("payment cancellation")
