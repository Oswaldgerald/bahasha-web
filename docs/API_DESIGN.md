# Bahasha Mobile API Design

Status: proposed contract, no API implementation yet  
Target framework: Django Ninja  
Initial client: Bahasha congregation-member mobile application

## 1. Purpose

The first public API serves approved congregation members. It does not expose the
administrative web application as CRUD endpoints. Church administrators continue
to use the server-rendered web interface, while the mobile API gives each member
access only to their own identity, contribution categories, targets, contribution
history, and church announcements.

The mobile design shown for Ahadi, Jengo, Uwakili, Jumuiya, and Mavuno must be
server-driven. Category names, presentation metadata, availability, totals, and
weekly entries come from the API instead of being compiled into the mobile app.
The primary member journey is to open a contribution-category card, review the
current and missed weeks for that category, select one or more eligible weeks, and
complete one mobile-money payment for the selected allocations.

## 2. Design Decisions

1. All public endpoints are versioned under `/api/v1/`.
2. Django Ninja routers are split by the Django app that owns the feature.
3. Mobile authentication uses short-lived bearer access tokens and rotating,
   revocable refresh tokens. Browser session cookies remain web-only.
4. Every member query is scoped from the authenticated user. Member and church
   IDs are never accepted from the mobile client to establish ownership.
5. Mobile users cannot directly create a posted `Contribution` record.
6. A mobile contribution starts as a payment intent. A verified payment-provider
   callback posts the contribution through `contributions.services.save_contribution`.
7. Missing-week status is calculated by the server from church weeks and posted
   member contributions; the mobile app never decides whether a week is missing.
8. One payment intent may settle multiple eligible weeks within one category.
9. Financial amounts are JSON strings with an ISO currency code, never floats.
10. Dates and timestamps use ISO 8601. Server timestamps are UTC.
11. Public resources use UUID identifiers. Sequential database primary keys remain
   internal implementation details.
12. Every endpoint declares request and response schemas so the generated OpenAPI
    document is the source of truth for mobile integration.

## 3. Versioning and Documentation

- API base: `/api/v1/`
- OpenAPI schema: `/api/v1/openapi.json`
- Interactive documentation: `/api/v1/docs`
- Django Ninja API version: `1.0.0`

Breaking response or behavior changes require `/api/v2/`. Additive optional fields
may be introduced within v1. Mobile clients must ignore unknown response fields.
Interactive documentation should be disabled or staff-protected in production;
the OpenAPI artifact can be generated during CI for mobile developers.

Django Ninja supports router composition and URL-prefix versioning. The proposed
layout follows its documented router and versioning model:

- [Routers](https://django-ninja.dev/guide/routers/)
- [Versioning](https://django-ninja.dev/guide/versioning/)
- [Authentication](https://django-ninja.dev/guide/authentication/)
- [Responses](https://django-ninja.dev/guide/responses/)

## 4. Proposed Module Layout

```text
config/
  api.py                         # NinjaAPI instance, handlers, router mounting
api/
  common/
    errors.py                    # stable error codes and exception handlers
    pagination.py                # cursor pagination contract
    schemas.py                   # money, metadata, message schemas
    throttling.py
  v1/
    router.py                    # v1 router composition only
users/
  api/
    auth.py                      # bearer authentication implementation
    router.py                    # token and profile operations
    schemas.py
  tokens.py                      # token issue, rotate, and revoke services
members/
  api/
    router.py                    # current member and bootstrap operations
    schemas.py
contributions/
  api/
    router.py                    # member-scoped history and summaries
    schemas.py
payments/
  api/
    router.py                    # intents and provider callbacks
    schemas.py
  services.py                    # provider-neutral payment orchestration
notifications/
  api/
    router.py
    schemas.py
```

Routers are thin transport adapters. Business rules stay in each app's service
module and are shared by web views, APIs, imports, and payment callbacks.

## 5. Authentication Contract

### Access and refresh tokens

- Access token lifetime: 15 minutes.
- Refresh token lifetime: 30 days when the device is trusted.
- Refresh tokens are rotated on every refresh and stored as hashes.
- Reusing a rotated token revokes that token family.
- Logout revokes the current device session.
- Password change, account deactivation, member rejection, or church deactivation
  revokes all member refresh tokens.
- Access tokens contain only stable authorization claims: user UUID, role, church
  UUID, token session UUID, issued-at, and expiry.
- The database remains authoritative for active and approved status.

The bearer implementation may use a maintained JWT package or a small Django Ninja
`HttpBearer` authenticator. Package selection is an implementation decision; it
must not alter the HTTP contract below.

### Login eligibility

A login succeeds only when all conditions are true:

- User account is active.
- Role is `MEMBER` for member-mobile endpoints.
- A related member profile exists.
- Member is active and `APPROVED`.
- Church is active.

The initial identifier accepts a username or normalized international phone number.
Email is used for password recovery, not as an assumed login identifier.

## 6. Endpoint Catalogue

### Authentication

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/auth/token` | Exchange identifier, password, and device details for tokens |
| `POST` | `/api/v1/auth/token/refresh` | Rotate refresh token and return a new token pair |
| `POST` | `/api/v1/auth/logout` | Revoke the current device session |
| `POST` | `/api/v1/auth/password/forgot` | Send a generic password-reset response without account discovery |

Authentication endpoints receive strict per-IP and per-identifier throttling.
`password/forgot` always returns `202`, whether or not the email exists.

Token request:

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

Token response:

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

### Current member and mobile startup

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/me` | Current member identity, church, Jumuiya, and church groups |
| `PATCH` | `/api/v1/me` | Update explicitly allowed profile fields only |
| `GET` | `/api/v1/me/photo` | Return the authenticated member's protected photo |
| `POST` | `/api/v1/me/photo` | Replace the member's profile photo |
| `DELETE` | `/api/v1/me/photo` | Remove the member's profile photo |
| `GET` | `/api/v1/bootstrap` | Mobile startup payload with profile, active period, tiles, and capabilities |

The first bootstrap response prevents the mobile home screen from making several
independent requests. It is not a replacement for the canonical detail endpoints.
The initial profile update allowlist is `full_name` and `email`. Phone-number
changes require a future verification workflow and are not accepted by `PATCH /me`.

### Categories, targets, and history

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/contribution-categories` | Active mobile-enabled category tiles and member totals |
| `GET` | `/api/v1/contribution-categories/{category_uuid}` | Category summary for the active or selected year |
| `GET` | `/api/v1/contribution-categories/{category_uuid}/weeks` | Payable, paid, missing, and upcoming weeks for one category |
| `GET` | `/api/v1/contributions` | Cursor-paginated contribution history owned by the member |
| `GET` | `/api/v1/contributions/{contribution_uuid}` | One owned contribution receipt/detail |
| `GET` | `/api/v1/targets` | Member annual targets and progress by category |
| `GET` | `/api/v1/financial-years` | Years available for the member's church |

Supported history filters:

- `category_id`
- `financial_year`
- `status`
- `cursor`
- `page_size` with a maximum of 50

The default ordering is newest contribution date and newest creation time first.

#### Category cards

The category collection is the source for the mobile dashboard cards. Each card
contains a stable `key`, localized labels, icon key, theme color, frequency,
payment availability, total contributed, and missing-week count. The mobile app
may control card layout, but it must not hardcode which categories exist or whether
they accept payments.

Example card:

```json
{
  "id": "c74f9636-90c5-47b4-a854-e4515feb4907",
  "key": "ahadi",
  "labels": {"default": "Ahadi", "sw": "Ahadi"},
  "description": "Track and settle your weekly promise offerings.",
  "icon": "hand-heart",
  "color": "#A844B7",
  "frequency": "weekly",
  "display_order": 1,
  "payments_enabled": true,
  "allows_catch_up": true,
  "missing_weeks_count": 2,
  "total_contributed": {"amount": "16500.00", "currency": "TZS"}
}
```

#### Missing-week calculation

For a weekly category, the server combines `ContributionWeek` records from the
selected financial year with the authenticated member's posted contributions for
that category. Each week has one of these states:

- `paid`: one or more posted contributions exist for that week and category.
- `missing`: the week is current or past, accepts catch-up payment, and has no
  posted contribution.
- `partial`: posted total is below an expected weekly amount when such an amount
  is configured.
- `upcoming`: the Sunday date is in the future.
- `unavailable`: the week cannot receive a member payment under church policy.

A failed or pending payment never marks a week as paid. A closed administrative
week does not automatically decide catch-up eligibility; that is controlled by a
separate church/category policy. Non-weekly categories return an empty weekly
schedule and accept an unallocated category payment when enabled.

Example weekly schedule item:

```json
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
```

### Notifications

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/notifications` | Cursor-paginated sent announcements visible to the member |
| `POST` | `/api/v1/notifications/{notification_uuid}/read` | Mark one notification as read |
| `POST` | `/api/v1/devices` | Register or rotate a mobile push token |
| `DELETE` | `/api/v1/devices/{device_uuid}` | Unregister a device |

### Payments and making a contribution

These endpoints are designed now but implemented only after a payment provider is
selected and the payment models exist.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/payment-methods` | Payment methods currently available for the member's church |
| `POST` | `/api/v1/payment-intents` | Start a contribution payment for the authenticated member |
| `GET` | `/api/v1/payment-intents` | Recent and incomplete payment intents owned by the member |
| `GET` | `/api/v1/payment-intents/{intent_uuid}` | Poll provider/payment state |
| `POST` | `/api/v1/payment-intents/{intent_uuid}/cancel` | Cancel an intent when the provider permits it |
| `POST` | `/api/v1/webhooks/payments/{provider}` | Receive and verify provider callbacks |

`POST /payment-intents` requires an `Idempotency-Key` header. Repeating the same key
and body returns the original intent. Reusing the key with a different body returns
`409 IDEMPOTENCY_CONFLICT`.

Payment intent request:

```json
{
  "category_id": "c74f9636-90c5-47b4-a854-e4515feb4907",
  "currency": "TZS",
  "payment_method": "mobile_money",
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

Accepted payment intent:

```json
{
  "id": "8c65398e-b044-4891-84fe-f3fa9daf1fea",
  "status": "pending_customer_action",
  "amount": {"amount": "10000.00", "currency": "TZS"},
  "category": {"id": "...", "key": "ahadi", "name": "Ahadi"},
  "allocations": [
    {"week_number": 3, "amount": {"amount": "5000.00", "currency": "TZS"}},
    {"week_number": 4, "amount": {"amount": "5000.00", "currency": "TZS"}}
  ],
  "provider_reference": null,
  "expires_at": "2026-10-09T12:30:00Z",
  "next_action": {
    "type": "approve_mobile_money_prompt",
    "message": "Approve the payment request on your phone."
  }
}
```

All allocations in one intent belong to the same category, member, church, and
financial year. The server verifies that allocation amounts sum to the intent total
and that every selected week is payment-eligible before contacting the provider.

Only a verified provider callback may change a payment to `SUCCEEDED`. On that
transition, the payment service atomically creates one `ONLINE_PAYMENT` contribution
per allocation and calls `save_contributions`. Each posted record preserves its own
week while sharing the payment intent reference. Duplicate callbacks must never
create duplicate contributions.

Payment intent states are `created`, `pending_customer_action`, `processing`,
`succeeded`, `failed`, `expired`, and `cancelled`. Only the server-side payment
service moves an intent through these states. A successful response includes the
resulting contribution UUIDs so the app can open receipts and refresh the selected
category schedule.

#### Mobile payment journey

1. `GET /bootstrap` renders the available sadaka cards.
2. The member opens a card and the app requests its detail and weekly schedule.
3. The member selects the current week, one missed week, or several missed weeks.
4. The app displays the exact allocation and total before confirmation.
5. The app creates one idempotent payment intent.
6. The member completes the provider action, such as approving a mobile-money
   prompt on the registered phone.
7. The app polls the intent or receives a push update while the provider callback
   is processed.
8. After success, the app refreshes the category schedule; settled weeks now return
   `paid`, and the card total and missing-week count are updated.

The app must keep failed and cancelled payment attempts separate from missing-week
state. A week remains missing until a posted contribution exists.

## 7. Core Response Shapes

### Bootstrap

```json
{
  "member": {
    "id": "08b768d8-454a-48f0-b8cc-1b17cbfd65ad",
    "full_name": "Amina Mushi",
    "bahasha_number": "BHS-00412",
    "phone_number": "+255700000000",
    "photo_url": "/api/v1/me/photo",
    "church": {"id": "...", "name": "Bahasha Parish"},
    "jumuiya": {"id": "...", "name": "Mt. Yosefu"}
  },
  "active_period": {
    "financial_year": 2026,
    "week": {"number": 41, "sunday_date": "2026-10-11", "is_closed": false}
  },
  "categories": [
    {
      "id": "...",
      "key": "ahadi",
      "name": "Ahadi",
      "icon": "hand-heart",
      "color": "#A844B7",
      "can_contribute": true,
      "allows_catch_up": true,
      "missing_weeks_count": 2,
      "total_contributed": {"amount": "16500.00", "currency": "TZS"}
    }
  ],
  "capabilities": {
    "payments_enabled": false,
    "profile_photo_upload": true,
    "push_notifications": false
  }
}
```

### Contribution list item

```json
{
  "id": "...",
  "reference": "CONT-2026-000018",
  "category": {"id": "...", "key": "ahadi", "name": "Ahadi"},
  "week": {"number": 3, "sunday_date": "2026-09-15"},
  "amount": {"amount": "5000.00", "currency": "TZS"},
  "status": "posted",
  "contribution_date": "2026-09-15",
  "posted_at": "2026-09-15T10:24:18Z"
}
```

### Paginated collection

```json
{
  "items": [],
  "page": {
    "next_cursor": null,
    "has_more": false
  }
}
```

### Error

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

Stable error codes include `AUTHENTICATION_FAILED`, `TOKEN_EXPIRED`,
`ACCOUNT_INACTIVE`, `MEMBER_NOT_APPROVED`, `FORBIDDEN`, `NOT_FOUND`,
`VALIDATION_ERROR`, `RATE_LIMITED`, `IDEMPOTENCY_CONFLICT`,
`PAYMENTS_UNAVAILABLE`, and `PROVIDER_ERROR`.

## 8. HTTP Behavior

- `200`: successful read or update
- `201`: new resource created
- `202`: asynchronous payment or recovery request accepted
- `204`: successful logout, deletion, or idempotent read-state update
- `400`: malformed request outside schema validation
- `401`: missing, invalid, expired, or revoked token
- `403`: authenticated but outside the permitted role or state
- `404`: resource absent or not owned by the member
- `409`: idempotency or state-transition conflict
- `422`: schema or field validation failure
- `429`: throttled request

Return `404`, not `403`, for another member's resource to avoid confirming that it
exists. Responses include `X-Request-ID`. Mutating responses use `Cache-Control:
no-store`; member data responses are private and must not be cached by shared proxies.

## 9. Authorization Rules

Every member router uses one authorization dependency that resolves an approved,
active member from `request.auth`. All querysets additionally filter by both member
and church. Endpoint code must never do this:

```python
Member.objects.get(id=payload.member_id)
```

It must derive ownership from authentication:

```python
member = request.auth.member
Contribution.objects.filter(member=member, church=member.church)
```

Administrative APIs, if needed later, use a separate router and permission policy
under `/api/internal/v1/`; they are not added to the member token's scope.

## 10. Required Model Work Before Implementation

The current schema is not yet sufficient for the complete contract. The web/domain
foundation for item 2 and the category ownership decision in item 9 is complete:
categories are church-scoped, have stable public UUIDs, expose configurable mobile
presentation and payment fields, and are seeded with editable defaults when a
church is created. This does not expose an API; Ninja schemas and routes remain
future work.

1. Add stable public UUIDs to users, members, churches, categories, contributions,
   financial years, weeks, notifications, and targets.
2. Completed in the domain model: category mobile metadata includes `key`, optional
   Swahili label, `icon_key`, `theme_color`, `is_mobile_visible`,
   `allows_member_payment`, and `allows_catch_up`.
3. Add refresh-token sessions with token hash, family, device, expiry, revocation,
   last-used timestamp, and last-seen IP metadata.
4. Add mobile-device records for push tokens and platform metadata.
5. Add per-user notification receipts; the current notification model cannot track
   read state for individual users.
6. Add `PaymentIntent`, `PaymentIntentAllocation`, `PaymentAttempt`, and
   `PaymentWebhookEvent` models before enabling mobile payments.
7. Link each payment allocation to at most one contribution and enforce uniqueness
   for intent, category, and selected contribution week.
8. Add an optional weekly expectation/commitment model if the product must
   distinguish partially paid weeks from weeks with any posted payment.
9. Completed: contribution categories are church-owned. Names, keys, and codes are
   unique within each church, and default records remain fully editable.

The API must not reuse the current administrative dashboard query directly because
that aggregation is system-wide. Mobile summary queries are always member- and
church-scoped.

## 11. Security and Operations

- HTTPS is mandatory outside local development.
- Secrets and signing keys come from environment variables and support rotation.
- Authentication throttling is backed by a shared production cache. Django Ninja's
  application throttles are supplemental; the reverse proxy also rate-limits login,
  password recovery, and webhooks.
- Provider webhooks use signature verification, replay protection, event storage,
  and idempotent processing.
- Raw passwords, bearer tokens, refresh tokens, payment secrets, and full provider
  payloads are never written to application logs.
- Audit login, logout, token-family revocation, profile changes, payment state
  changes, and contribution posting.
- Set explicit request body and image upload size limits.
- OpenAPI schemas and API contract tests run in CI.

## 12. Delivery Plan

### Phase 1: Foundation

- Add Django Ninja and mount an empty versioned API with a health operation.
- Add public UUID and category metadata migrations.
- Implement common schemas, errors, request IDs, pagination, and contract tests.

### Phase 2: Member authentication

- Implement token sessions, rotation, revocation, and throttling.
- Implement `/auth/*`, `/me`, protected photo access, and account-state tests.

### Phase 3: Read-only mobile experience

- Implement bootstrap, category cards, weekly payment-state schedules, targets,
  history, and financial years.
- Validate the payloads against the mobile home and Ahadi detail screens.
- Add query-count and cross-member authorization tests.

### Phase 4: Notifications

- Add receipts and devices, then expose announcement and read-state operations.

### Phase 5: Payments

- Select a provider and document its state machine and signature rules.
- Add payment models, multi-week allocations, idempotent intent creation, webhooks,
  reconciliation, and atomic contribution posting.
- Enable `payments_enabled` only after sandbox and failure-path testing succeeds.

## 13. Definition of Ready for API Coding

Implementation starts after these product decisions are confirmed:

- Member login identifier: username, phone number, or both.
- Password recovery channel: email initially, or SMS/OTP.
- Canonical category keys and mobile presentation metadata.
- Whether every category accepts direct member payments.
- Which categories are weekly and whether members can settle closed/past weeks.
- Whether a missing week means no payment or an amount below a weekly commitment.
- First payment provider and its supported Tanzania payment flows.
- Mobile deep-link domains for password recovery and payment return paths.
- Retention periods for token sessions, webhook events, and device registrations.

Until those decisions are made, the safest first implementation is foundation plus
read-only member data. Payment endpoints remain documented but disabled.
