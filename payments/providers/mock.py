"""Development-only mobile-money provider backed by deterministic JSON fixtures."""

import json
from pathlib import Path

from .base import (
    PaymentProvider,
    PaymentProviderError,
    PaymentProviderResult,
    PaymentProviderStatus,
)


class MockPaymentProvider(PaymentProvider):
    """Simulate provider initiation and status queries without network access."""

    display_name = "Mock mobile money"

    def __init__(self, *, provider_key, scenario_name, fixture_path):
        """Load one named scenario while retaining the requested provider key."""

        self.key = provider_key
        self.scenario_name = scenario_name
        self.fixture_path = Path(fixture_path)
        self.scenario = self._load_scenario()

    @property
    def configured(self):
        """A successfully loaded fixture is sufficient for local simulation."""

        return True

    def initiate(self, payment):
        """Return the fixture's prompt result for a validated payment request."""

        return self._stage_result("initiate", payment)

    def query(self, payment):
        """Return the fixture's authoritative settlement result."""

        return self._stage_result("query", payment)

    def cancel(self, payment):
        """Return the fixture's cancellation result when one is configured."""

        return self._stage_result("cancel", payment)

    def _load_scenario(self):
        """Read and validate the selected scenario from the configured JSON file."""

        try:
            data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
            scenario = data["scenarios"][self.scenario_name]
        except FileNotFoundError as error:
            raise PaymentProviderError(
                "MOCK_FIXTURE_NOT_FOUND",
                "The mock payment fixture could not be found.",
            ) from error
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise PaymentProviderError(
                "MOCK_FIXTURE_INVALID",
                "The mock payment fixture or scenario is invalid.",
            ) from error
        return scenario

    def _stage_result(self, stage_name, payment):
        """Translate one fixture stage into the provider-neutral result contract."""

        stage = self.scenario.get(stage_name)
        if not isinstance(stage, dict):
            raise PaymentProviderError(
                "MOCK_STAGE_UNAVAILABLE",
                f"The mock scenario does not define {stage_name}.",
            )
        error = stage.get("error")
        if error:
            raise PaymentProviderError(
                error.get("code", "MOCK_PROVIDER_ERROR"),
                error.get("message", "The mock provider rejected the payment."),
                retryable=bool(error.get("retryable", False)),
                status_code=error.get("status_code"),
            )
        try:
            status = PaymentProviderStatus(stage["status"])
        except (KeyError, ValueError) as error:
            raise PaymentProviderError(
                "MOCK_STATUS_INVALID",
                "The mock provider status is invalid.",
            ) from error
        suffix = payment.conversation_id.replace("-", "")[:20].upper()
        return PaymentProviderResult(
            status=status,
            provider_reference=stage.get("provider_reference") or f"MOCK-{suffix}",
            conversation_id=payment.conversation_id,
            transaction_id=(
                stage.get("transaction_id")
                or (f"MOCK-TXN-{suffix}" if status == PaymentProviderStatus.SUCCEEDED else None)
            ),
            response_code=stage.get("response_code", "0"),
            response_description=stage.get("response_description", ""),
            raw_response={"mock": True, "scenario": self.scenario_name},
        )
