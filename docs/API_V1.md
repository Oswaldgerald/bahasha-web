# Bahasha API v1 Contract

Status: implemented through member read experience and notification/device state;
payment processing remains disabled pending provider selection

Base path: `/api/v1`

Target framework: Django Ninja

Primary client: Bahasha congregation-member mobile application

This document is the normative HTTP contract for the first Bahasha mobile API.
`docs/API_DESIGN.md` explains the architecture and delivery plan behind it. If the
two documents disagree about an HTTP request or response, this contract wins.

## 1. Scope

API v1 serves approved congregation members. It provides:

- member authentication and device sessions;
- the authenticated member's profile and church context;
- server-configured contribution-category cards;
- contribution targets, history, receipts, and weekly status;
- current and missed-week payment selection;
- church announcements and notification read state; and
- provider-neutral payment intents and status tracking.

Administrative CRUD remains in the web application. Staff APIs are not exposed
under this member namespace. A future staff API must use a separate route and
permission policy, such as `/api/internal/v1`.

## 2. Contract Conventions

### URLs and media types

- All endpoints below are relative to `/api/v1`.
- JSON requests use `Content-Type: application/json`.
- JSON responses use `application/json; charset=utf-8`.
- Profile-photo uploads use `multipart/form-data`.
- Field names use `snake_case`.
- Resource identifiers are UUID strings. Database integer IDs are never public.
- Dates use `YYYY-MM-DD`.
- Timestamps use UTC ISO 8601, for example `2026-10-10T08:30:00Z`.
- Amounts are decimal strings and are never JSON floating-point numbers.
- API enums are lowercase `snake_case` strings.

### Common headers

| Header | Required | Usage |
| --- | --- | --- |
| `Authorization: Bearer <token>` | Protected endpoints | Member access token |
| `Accept-Language: sw` or `en` | No | Preferred display language; defaults to `sw` |
| `X-Request-ID` | No | Client request identifier; generated when absent and echoed in responses |
| `Idempotency-Key` | Payment creation | UUID generated once for one logical payment submission |

Clients must ignore unknown response fields. Removing or changing the meaning of a
documented field requires API v2. New optional fields may be added to v1.

### Money

```json
{
  "amount": "16500.00",
  "currency": "TZS"
}
```

TZS is the only supported v1 currency. The currency field remains explicit so the
contract can evolve without changing every money schema.

### Pagination

Collections use opaque cursor pagination:

```json
{
  "items": [],
  "page": {
    "next_cursor": null,
    "has_more": false
  }
}
```

`page_size` defaults to 20 and may range from 1 to 50. Clients must treat cursors
as opaque values and must not construct or modify them.

### Errors

```json
{
  "error": {
    "code": "MEMBER_NOT_APPROVED",
    "message": "Your membership is awaiting approval.",
    "fields": {},
    "request_id": "01J9Q4V6SP8K3W7E8J2D3M5N6P"
  }
}
```

`message` is suitable for display but is not a stable programmatic value. Mobile
logic branches on `code`. Validation errors use `fields`, where each key maps to a
list of messages.

Stable v1 error codes:

| Code | HTTP status | Meaning |
| --- | --- | --- |
| `AUTHENTICATION_FAILED` | 401 | Invalid identifier or password |
| `TOKEN_INVALID` | 401 | Token cannot be verified |
| `TOKEN_EXPIRED` | 401 | Access or refresh token expired |
| `TOKEN_REVOKED` | 401 | Device session was revoked |
| `ACCOUNT_INACTIVE` | 403 | User account is inactive |
| `MEMBER_NOT_APPROVED` | 403 | Member is pending or rejected |
| `CHURCH_INACTIVE` | 403 | Member's church is inactive |
| `FORBIDDEN` | 403 | Authenticated but operation is not allowed |
| `NOT_FOUND` | 404 | Resource is absent or is not owned by the member |
| `VALIDATION_ERROR` | 422 | Request fields or business rules are invalid |
| `STATE_CONFLICT` | 409 | Resource cannot transition from its current state |
| `IDEMPOTENCY_CONFLICT` | 409 | Idempotency key was reused with a different payload |
| `RATE_LIMITED` | 429 | Request limit exceeded |
| `PAYMENTS_UNAVAILABLE` | 503 | Church or provider cannot currently accept payments |
| `PROVIDER_ERROR` | 502 | Upstream payment provider failed |
| `INTERNAL_ERROR` | 500 | Unexpected server failure |

Another member's resource always returns `404`, not `403`.

## 3. Authentication and Authorization

Access tokens live for 15 minutes. Refresh tokens live for 30 days, rotate on every
use, and are stored only as hashes. Reuse of a rotated refresh token revokes the
entire token family. Logout revokes one device session. Password change, account
deactivation, member rejection, or church deactivation revokes every session for
that member.

A member-mobile login is eligible only when:

- the user is active and has role `MEMBER`;
- a related member profile exists;
- the member is active and approved; and
- the member's church is active.

Every protected query derives member and church ownership from `request.auth`.
Requests never accept a member ID or church ID to establish ownership.

## 4. Endpoint Summary

### Platform and authentication

| Method | Path | Auth | Success |
| --- | --- | --- | --- |
| `GET` | `/health` | No | `200` |
| `POST` | `/auth/token` | No | `200` |
| `POST` | `/auth/token/refresh` | Refresh token | `200` |
| `POST` | `/auth/logout` | Access token | `204` |
| `POST` | `/auth/password/forgot` | No | `202` |

### Member and startup

| Method | Path | Success |
| --- | --- | --- |
| `GET` | `/me` | `200` |
| `PATCH` | `/me` | `200` |
| `GET` | `/me/photo` | `200` or `404` |
| `POST` | `/me/photo` | `200` |
| `DELETE` | `/me/photo` | `204` |
| `GET` | `/bootstrap` | `200` |

### Contributions

| Method | Path | Success |
| --- | --- | --- |
| `GET` | `/financial-years` | `200` |
| `GET` | `/contribution-categories` | `200` |
| `GET` | `/contribution-categories/{category_id}` | `200` |
| `GET` | `/contribution-categories/{category_id}/weeks` | `200` |
| `GET` | `/targets` | `200` |
| `GET` | `/contributions` | `200` |
| `GET` | `/contributions/{contribution_id}` | `200` |

### Notifications and devices

| Method | Path | Success |
| --- | --- | --- |
| `GET` | `/notifications` | `200` |
| `POST` | `/notifications/{notification_id}/read` | `204` |
| `POST` | `/devices` | `201` or `200` |
| `DELETE` | `/devices/{device_id}` | `204` |

### Payments

| Method | Path | Success |
| --- | --- | --- |
| `GET` | `/payment-methods` | `200` |
| `POST` | `/payment-intents` | `202` |
| `GET` | `/payment-intents` | `200` |
| `GET` | `/payment-intents/{payment_intent_id}` | `200` |
| `POST` | `/payment-intents/{payment_intent_id}/cancel` | `200` |
| `POST` | `/webhooks/payments/{provider}` | `200` |

## 5. Platform and Authentication

### `GET /health`

Returns API and database readiness without exposing infrastructure details.

```json
{
  "status": "healthy",
  "api_version": "1.0.0",
  "database": "available"
}
```

### `POST /auth/token`

The identifier accepts a username or normalized international phone number.

```json
{
  "identifier": "+255700000000",
  "password": "member-password",
  "device": {
    "installation_id": "7dfef7df-8637-43a6-a4dc-4e52411a58a3",
    "platform": "android",
    "app_version": "1.0.0",
    "device_name": "Pixel 8"
  }
}
```

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "Bearer",
  "expires_in": 900,
  "member": {
    "id": "08b768d8-454a-48f0-b8cc-1b17cbfd65ad",
    "full_name": "Amina Mushi",
    "approval_status": "approved"
  }
}
```

Invalid credentials return the same response regardless of whether the identifier
exists. Login and refresh endpoints are rate-limited by both IP and identifier.

### `POST /auth/token/refresh`

```json
{"refresh_token": "..."}
```

Returns the same token-pair shape as login, with a newly rotated refresh token.

### `POST /auth/logout`

Revokes the current token session. Repeated logout is idempotent and returns `204`.

### `POST /auth/password/forgot`

```json
{"email": "member@example.org"}
```

Always returns `202` with a generic message. Email is the initial recovery channel;
SMS or OTP recovery is outside v1 until phone ownership verification exists.

## 6. Member and Bootstrap

### Member schema

```json
{
  "id": "08b768d8-454a-48f0-b8cc-1b17cbfd65ad",
  "full_name": "Amina Mushi",
  "username": "amina",
  "email": "amina@example.org",
  "phone_number": "+255700000000",
  "bahasha_number": "BHS-00412",
  "gender": "female",
  "marital_status": "married",
  "approval_status": "approved",
  "photo_url": "/api/v1/me/photo",
  "church": {
    "id": "958f3590-e25c-4c3f-91dc-76d09ab391c2",
    "code": "0001",
    "name": "Kijitonyama"
  },
  "jumuiya": {
    "id": "550782f7-35b1-40d3-8df5-dd694f9744c9",
    "name": "Mt. Yosefu"
  },
  "church_groups": [
    {"id": "47921ea2-55c2-4835-96c8-c5467a7dd6ab", "name": "Choir"}
  ]
}
```

`PATCH /me` accepts only `full_name` and `email`. Phone changes require a later
verified workflow. Church, role, approval, Bahasha number, Jumuiya, and groups are
staff-managed and read-only to mobile members.

Photo uploads accept JPEG, PNG, or WebP, with a maximum configured size of 5 MB.
The server validates actual image content and stores a normalized image. The photo
endpoint requires authentication and is not a public media URL.

### `GET /bootstrap`

This endpoint supplies the first mobile screen in one request. Canonical detail
endpoints remain available for refresh and pagination.

```json
{
  "member": {},
  "active_period": {
    "financial_year": {
      "id": "7cc609fd-ddc5-44cd-94e5-67664cc468aa",
      "year": 2026
    },
    "week": {
      "id": "59a58fa4-b400-45b3-a2dc-ae0652219462",
      "number": 41,
      "sunday_date": "2026-10-11",
      "is_closed": false
    }
  },
  "categories": [],
  "unread_notifications_count": 0,
  "capabilities": {
    "payments_enabled": false,
    "profile_photo_upload": true,
    "push_notifications": false
  }
}
```

An absent active financial year or week is represented by `null`, not by a `404`.

## 7. Contribution Categories and Weeks

Only categories belonging to the member's church with `is_active=true` and
`is_mobile_visible=true` are returned. Ordering is `display_order`, then name.

### Category card

```json
{
  "id": "c74f9636-90c5-47b4-a854-e4515feb4907",
  "key": "ahadi",
  "labels": {
    "default": "Ahadi",
    "sw": "Ahadi"
  },
  "description": "Track and settle your weekly promise offerings.",
  "icon": "hand-heart",
  "color": "#A844B7",
  "frequency": "weekly",
  "display_order": 1,
  "payments_enabled": true,
  "allows_catch_up": true,
  "amount_guidance": {
    "suggested": {"amount": "5000.00", "currency": "TZS"},
    "minimum": null,
    "maximum": null
  },
  "missing_weeks_count": 2,
  "total_contributed": {"amount": "16500.00", "currency": "TZS"}
}
```

`GET /contribution-categories` accepts optional `financial_year_id`. It defaults to
the church's active year. `GET /contribution-categories/{category_id}` returns the
same card plus target progress and contribution summary.

### Weekly schedule

`GET /contribution-categories/{category_id}/weeks` accepts:

- `financial_year_id` (optional UUID, defaults to active year);
- `state` (optional: `paid`, `missing`, `upcoming`, `unavailable`); and
- `page_size` and `cursor`.

```json
{
  "items": [
    {
      "id": "59a58fa4-b400-45b3-a2dc-ae0652219462",
      "week_number": 3,
      "sunday_date": "2026-09-15",
      "state": "missing",
      "payment_eligible": true,
      "contributed": {"amount": "0.00", "currency": "TZS"},
      "expected": null,
      "remaining": null
    }
  ],
  "page": {"next_cursor": null, "has_more": false}
}
```

For initial v1, `paid` means at least one posted contribution exists for that member,
category, and week. `missing` means the current or a past week has no posted
contribution and category catch-up is enabled. `upcoming` is a future Sunday.
`unavailable` covers a category that does not accept member payment or a week that
fails server policy. Pending or failed payments never mark a week paid.

The initial contract does not emit `partial`, because the current model has no
member-specific weekly commitment. Suggested category amounts are guidance, not a
debt. A future commitment model may add `partial` as an additive state.

For categories that allow catch-up, a closed administrative week may still be
settled through a verified mobile payment. Non-weekly categories return an empty
weekly collection and may accept one unallocated category payment.

## 8. Targets and Contribution History

### `GET /targets`

Query parameters: `financial_year_id` and `category_id`, both optional UUIDs.

```json
{
  "items": [
    {
      "id": "e1d26cb0-ddf3-4700-a58a-aa8311fe3315",
      "financial_year": {"id": "...", "year": 2026},
      "category": {"id": "...", "key": "ahadi", "name": "Ahadi"},
      "target": {"amount": "100000.00", "currency": "TZS"},
      "contributed": {"amount": "16500.00", "currency": "TZS"},
      "remaining": {"amount": "83500.00", "currency": "TZS"},
      "completion_percentage": "16.50"
    }
  ],
  "page": {"next_cursor": null, "has_more": false}
}
```

### `GET /contributions`

Supported filters:

- `category_id` (UUID);
- `financial_year_id` (UUID);
- `week_id` (UUID);
- `status` (`posted`, `pending`, `reversed`);
- `date_from` and `date_to`;
- `page_size` and `cursor`.

Default ordering is newest contribution date, then newest creation time.

```json
{
  "items": [
    {
      "id": "fb7215c1-9598-40e1-b00f-736d520ec49d",
      "reference": "CONT-2026-000018",
      "category": {"id": "...", "key": "ahadi", "name": "Ahadi"},
      "week": {"id": "...", "number": 3, "sunday_date": "2026-09-15"},
      "amount": {"amount": "5000.00", "currency": "TZS"},
      "source": "online_payment",
      "status": "posted",
      "contribution_date": "2026-09-15",
      "posted_at": "2026-09-15T10:24:18Z"
    }
  ],
  "page": {"next_cursor": null, "has_more": false}
}
```

The detail endpoint additionally returns remarks, financial year, payment receipt
reference when applicable, and church identity. Members cannot create, edit, reverse,
or delete contribution records directly through API v1.

## 9. Notifications and Devices

Only notifications with `status=sent` that belong to the member's church and target
the member's role are visible.

```json
{
  "id": "7c72ac94-37de-47ca-8630-84f4a970a092",
  "type": "church_announcement",
  "title": "Sunday service",
  "message": "The service starts at 8:00.",
  "sent_at": "2026-10-10T06:00:00Z",
  "is_read": false,
  "read_at": null
}
```

Marking an already-read notification is idempotent. Device registration upserts by
`installation_id` and rotates the push token rather than creating duplicates.

```json
{
  "installation_id": "7dfef7df-8637-43a6-a4dc-4e52411a58a3",
  "platform": "android",
  "push_token": "provider-token",
  "app_version": "1.0.0"
}
```

Notification receipts and mobile-device models are prerequisites; these endpoints
remain unimplemented until those migrations exist.

## 10. Payments

Mobile clients never create a posted `Contribution` directly. They create a payment
intent. Only a verified provider callback may mark it successful and atomically post
its allocations through `contributions.services.save_contributions`.

### Payment methods

```json
{
  "items": [
    {
      "key": "mobile_money",
      "name": "Mobile money",
      "providers": ["vodacom_m_pesa", "airtel_money", "mixx_by_yas"],
      "currency": "TZS",
      "enabled": true
    }
  ]
}
```

### Create payment intent

`POST /payment-intents` requires `Idempotency-Key`. Repeating the same key and
canonical body returns the original response. Reusing a key with another body
returns `409 IDEMPOTENCY_CONFLICT`.

```json
{
  "category_id": "c74f9636-90c5-47b4-a854-e4515feb4907",
  "financial_year_id": "7cc609fd-ddc5-44cd-94e5-67664cc468aa",
  "payment_method": "mobile_money",
  "provider": "vodacom_m_pesa",
  "payer_phone_number": "+255700000000",
  "allocations": [
    {
      "contribution_week_id": "59a58fa4-b400-45b3-a2dc-ae0652219462",
      "amount": "5000.00"
    },
    {
      "contribution_week_id": "115727cb-035f-4a9f-8fc5-979aef221c10",
      "amount": "5000.00"
    }
  ]
}
```

For a non-weekly category, `allocations` contains one item with
`contribution_week_id: null`. All allocations in one intent must share one member,
church, category, financial year, and currency. The server calculates the total.

```json
{
  "id": "8c65398e-b044-4891-84fe-f3fa9daf1fea",
  "status": "pending_customer_action",
  "amount": {"amount": "10000.00", "currency": "TZS"},
  "category": {"id": "...", "key": "ahadi", "name": "Ahadi"},
  "allocations": [
    {
      "week": {"id": "...", "number": 3, "sunday_date": "2026-09-15"},
      "amount": {"amount": "5000.00", "currency": "TZS"}
    }
  ],
  "provider_reference": null,
  "contribution_ids": [],
  "expires_at": "2026-10-10T12:30:00Z",
  "next_action": {
    "type": "approve_mobile_money_prompt",
    "message": "Approve the payment request on your phone."
  }
}
```

Payment states:

```text
created -> pending_customer_action -> processing -> succeeded
   |                 |                   |
   +-> failed        +-> failed          +-> failed
   +-> cancelled     +-> cancelled
   +-> expired       +-> expired
```

`succeeded` is terminal. Provider callbacks are signature-verified, replay-protected,
stored, and idempotently processed. Duplicate callbacks must not duplicate
contributions. Every successful allocation maps to exactly one contribution.

Payment endpoints are part of the contract but remain disabled until a provider is
selected and payment persistence is implemented. While disabled,
`capabilities.payments_enabled` is false, payment methods are empty, and intent
creation returns `503 PAYMENTS_UNAVAILABLE`.

## 11. Caching, Rate Limits, and Observability

- Auth, payment, and mutation responses use `Cache-Control: no-store`.
- Member reads use `Cache-Control: private, no-store` initially.
- Login, password recovery, refresh, and payment creation are rate-limited by IP
  and member/identifier using a shared production cache.
- Every response carries `X-Request-ID`.
- Logs may contain request ID, route name, status, duration, user UUID, and church
  UUID. They must not contain passwords, tokens, full payment payloads, or secrets.
- Authentication events, session revocation, profile changes, payment transitions,
  and contribution posting create audit events.

## 12. OpenAPI

- Schema: `/api/v1/openapi.json`
- Interactive docs: `/api/v1/docs`
- API title: `Bahasha Member API`
- API version: `1.0.0`

Interactive docs are staff-protected or disabled in production. CI exports the
OpenAPI JSON and checks it for unintended breaking changes. Every operation uses a
stable `operation_id`, tags, explicit success schema, and the common error schema.

The current implementation disables interactive docs when `DEBUG` is false. The
OpenAPI schema remains available for mobile-client generation.

## 13. Implementation Status

Implemented:

1. Django Ninja and the versioned `/api/v1/` API.
2. Public UUIDs for all member-facing resources.
3. Opaque access and rotating refresh tokens stored only as hashes.
4. Member profile, protected photo, bootstrap, configurable categories, weeks,
   targets, contribution history, notification receipts, and device registration.
5. Cross-member and cross-church ownership enforcement with API behavior tests.

Still required before mobile payments can be enabled:

1. Select the first Tanzania payment provider and document signatures, timeout,
   retry, reconciliation, and sandbox behavior.
2. Add payment intent, allocation, attempt, and webhook-event models.
3. Add shared production-cache throttling for authentication and payment routes.
4. Add idempotency, callback replay, and payment failure-path tests.

Category public UUIDs and configurable mobile-card/payment fields already exist.
The API must reuse contribution services and must not update annual-target totals
directly.

## 14. Delivery Order

1. Foundation: Ninja, errors, request IDs, UUIDs, OpenAPI, and `/health`.
2. Authentication: token sessions, rotation, logout, and `/me`.
3. Read-only mobile app: bootstrap, categories, weeks, targets, and history.
4. Notifications: receipts, devices, listing, and read state.
5. Payments: persistence, provider adapter, intents, callbacks, reconciliation, and
   atomic contribution posting.

The mobile team can build against generated OpenAPI and fixture responses after
phase 1, while backend phases continue behind capability flags.
