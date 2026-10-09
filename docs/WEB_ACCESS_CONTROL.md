# Web Access Control

The web application applies role checks at the view boundary and church scoping at
the queryset and form boundaries. Navigation visibility mirrors these permissions,
but navigation is not treated as an authorization control.

| Capability | Roles |
| --- | --- |
| Staff dashboard | Main Pastor, Assistant Pastor, Congregation Elder, Administrator, Finance Officer, Auditor |
| Church and user administration | Main Pastor, Administrator |
| Member, Jumuiya, and church-group management | Main Pastor, Assistant Pastor, Congregation Elder, Administrator |
| Contribution operations, periods, uploads, and targets | Main Pastor, Administrator, Finance Officer |
| Reports | Main Pastor, Assistant Pastor, Congregation Elder, Administrator, Finance Officer, Auditor |
| Notifications | Main Pastor, Assistant Pastor, Administrator |
| Audit logs | Main Pastor, Administrator, Auditor |
| Personal profile | Every authenticated user |

Superusers have global access. Every non-superuser is restricted to the church on
their account. A staff user without a church assignment receives an empty church
scope instead of global access. Members are redirected to their profile after login
and cannot open staff management pages.

Church creation and Django administration are reserved for superusers. Church
administrators can view and edit only their assigned church.

Password reset actions send Django's signed, expiring reset link to the user's email
address. They never assign or expose a shared temporary password.
