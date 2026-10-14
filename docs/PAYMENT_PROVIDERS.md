# Mobile-money provider adapters

Bahasha isolates operator APIs behind `payments.providers.base.PaymentProvider`.
The mobile app calls Bahasha only; it must never receive operator client secrets,
API keys, merchant codes, or access tokens.

## Supported adapters

| Provider key | Adapter | Readiness |
| --- | --- | --- |
| `vodacom_m_pesa` | `MpesaProvider` | Sandbox contract implemented |
| `airtel_money` | `AirtelMoneyProvider` | Sandbox contract implemented |
| `mixx_by_yas` | `MixxProvider` | Contract shell; onboarding endpoints required |

Set `PAYMENT_PROVIDER` to one of these keys to select an adapter. Selection does
not enable public payment endpoints. `PAYMENTS_ENABLED` and the selected
provider's own `*_ENABLED` flag remain independent safety gates.

## Airtel Money

Register the application through the Airtel Tanzania developer portal and place
the issued credentials in server environment variables:

```dotenv
PAYMENT_PROVIDER=airtel_money
AIRTEL_MONEY_ENABLED=False
AIRTEL_MONEY_ENVIRONMENT=sandbox
AIRTEL_MONEY_CLIENT_ID=
AIRTEL_MONEY_CLIENT_SECRET=
```

The adapter supports OAuth client credentials, Tanzania collection initiation,
transaction-status queries, MSISDN normalization, and normalized results. Airtel
may assign a different API product or path version during approval; the base URL,
token path, collection path, and query path are therefore overrideable.

## Mixx by Yas

Mixx's public merchant material does not publish the complete direct collection
API contract. Obtain the approved sandbox contract from Mixx during merchant
onboarding, then configure every value below:

```dotenv
PAYMENT_PROVIDER=mixx_by_yas
MIXX_ENABLED=False
MIXX_ENVIRONMENT=sandbox
MIXX_BASE_URL=
MIXX_CLIENT_ID=
MIXX_CLIENT_SECRET=
MIXX_MERCHANT_CODE=
MIXX_TOKEN_PATH=
MIXX_COLLECTION_PATH=
MIXX_QUERY_PATH=
```

The Mixx adapter deliberately has no guessed URLs. It remains unconfigured until
all credentials and endpoint paths are present. Before enabling it, compare the
onboarding document's authentication request, collection payload, response fields,
and status values with `payments/providers/mixx.py`, then run contract tests in the
operator sandbox.

## Activation checklist

Do not enable member payments merely because an adapter is configured. Complete
payment-intent persistence, idempotency, verified callbacks or polling, allocation
uniqueness, atomic contribution posting, reconciliation, throttling, and audit
events first. An accepted handset prompt is not evidence of settlement.
