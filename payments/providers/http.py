"""Shared HTTP transport for mobile-money provider adapters."""

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import PaymentProviderError


logger = logging.getLogger(__name__)


class JsonHttpTransport:
    """Send JSON requests while keeping credentials and response bodies out of logs."""

    def __init__(self, error_prefix, provider_name):
        """Store safe provider labels used when translating transport failures."""

        self.error_prefix = error_prefix
        self.provider_name = provider_name

    def request(self, method, url, *, headers, payload=None, timeout=20):
        """Send one JSON request and return its decoded object response."""

        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=data,
            headers={"Accept": "application/json", "Content-Type": "application/json", **headers},
            method=method,
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except HTTPError as error:
            # Provider responses may contain personal or transaction information.
            # Consume the body without logging or returning it to callers.
            error.read()
            logger.warning(
                "%s returned HTTP %s for %s",
                self.provider_name,
                error.code,
                url,
            )
            raise PaymentProviderError(
                f"{self.error_prefix}_HTTP_ERROR",
                f"{self.provider_name} rejected the payment request.",
                retryable=error.code >= 500,
                status_code=error.code,
            ) from error
        except (TimeoutError, URLError) as error:
            logger.warning(
                "%s request failed for %s: %s",
                self.provider_name,
                url,
                type(error).__name__,
            )
            raise PaymentProviderError(
                f"{self.error_prefix}_UNAVAILABLE",
                f"{self.provider_name} could not be reached. Try again shortly.",
                retryable=True,
            ) from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PaymentProviderError(
                f"{self.error_prefix}_INVALID_RESPONSE",
                f"{self.provider_name} returned an invalid response.",
                retryable=True,
            ) from error

    def post(self, url, *, headers, payload, timeout):
        """Send a JSON POST request."""

        return self.request(
            "POST",
            url,
            headers=headers,
            payload=payload,
            timeout=timeout,
        )

    def get(self, url, *, headers, timeout):
        """Send a JSON GET request."""

        return self.request("GET", url, headers=headers, timeout=timeout)
