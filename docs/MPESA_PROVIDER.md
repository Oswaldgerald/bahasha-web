# Vodacom M-Pesa provider

Bahasha integrates with Vodacom Tanzania through the provider-neutral interface in
`payments.providers.base`. `MpesaProvider` is the only module that knows Vodacom's
request field names, authorization mechanism, and endpoint paths.

## Safety boundary

The mobile app must call Bahasha's `/api/v1/payment-intents` API. It must never call
M-Pesa directly or contain an API key, public key, or service-provider code.

The adapter currently implements:

- RSA-encrypted API-key authorization;
- Tanzania C2B single-stage request construction;
- transaction-status query construction;
- local Tanzanian MSISDN normalization;
- typed provider results and sanitized transport errors;
- injectable HTTP transport for deterministic tests.

Public payment endpoints intentionally remain disabled. Before enabling them, add
payment-intent persistence, allocation uniqueness, idempotency, verified settlement,
atomic contribution posting, reconciliation, rate limiting, and audit events. An
accepted C2B prompt is not proof that money was received.

## Configuration

Copy the payment variables from `.env.example` and obtain sandbox values from the
M-Pesa developer portal. Keep both switches false until sandbox settlement tests
pass:

```dotenv
PAYMENTS_ENABLED=False
MPESA_ENABLED=False
MPESA_ENVIRONMENT=sandbox
MPESA_API_KEY=
MPESA_PUBLIC_KEY=
MPESA_SERVICE_PROVIDER_CODE=
```

Store a multiline PEM public key as a single environment value with literal `\n`
separators. `MPESA_BASE_URL`, `MPESA_C2B_PATH`, and `MPESA_QUERY_PATH` may be
overridden if Vodacom assigns different endpoints during onboarding.

Production activation requires both an approved M-Pesa application and completed
Bahasha settlement/reconciliation tests. Changing `MPESA_ENVIRONMENT` alone must
not enable payments.
