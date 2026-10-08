import csv
import io
import re
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.text import slugify

from churches.models import Church
from jumuiya.models import Jumuiya
from users.models import User
from users.phone_numbers import normalize_phone_number, split_phone_number

from .models import Member
from .services import create_member


MEMBER_CSV_HEADERS = [
    "full_name",
    "phone_number",
    "email",
    "church_code",
    "jumuiya",
    "bahasha_number",
    "gender",
    "marital_status",
    "demographics",
    "approval_status",
    "is_active",
]
REQUIRED_MEMBER_CSV_HEADERS = {"full_name", "phone_number", "bahasha_number"}
MAX_MEMBER_CSV_ROWS = 5000


class MemberCsvError(Exception):
    pass


class MemberCsvImportError(MemberCsvError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("The CSV contains invalid member rows.")


@dataclass(frozen=True)
class MemberCsvImportResult:
    imported_count: int


def _header_name(value):
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def _choice_value(value, choices, field_name, default=""):
    normalized = (value or default).strip().upper()
    values = {key.upper(): key for key, _label in choices}
    labels = {label.upper(): key for key, label in choices}
    if normalized in values:
        return values[normalized]
    if normalized in labels:
        return labels[normalized]
    allowed = ", ".join(label for _key, label in choices)
    raise ValidationError(f"{field_name} must be one of: {allowed}.")


def _boolean_value(value, default=True):
    normalized = (value or "").strip().lower()
    if not normalized:
        return default
    if normalized in {"1", "true", "yes", "active"}:
        return True
    if normalized in {"0", "false", "no", "inactive"}:
        return False
    raise ValidationError("is_active must be Yes or No.")


def _error_messages(error):
    if isinstance(error, IntegrityError):
        return ["A member with the same unique account details already exists."]
    if hasattr(error, "message_dict"):
        return [
            f"{field}: {message}"
            for field, messages in error.message_dict.items()
            for message in messages
        ]
    if hasattr(error, "messages"):
        return list(error.messages)
    return [str(error)]


def _safe_csv_cell(value):
    text = str(value or "")
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


def _church_for_row(row, request_user):
    church_code = row.get("church_code", "").strip()
    if request_user.church_id and not request_user.is_superuser:
        church = request_user.church
        if church_code and church_code.casefold() != church.church_code.casefold():
            raise ValidationError(
                f"church_code must be {church.church_code} for your account."
            )
        return church
    if not church_code:
        raise ValidationError("church_code is required for system-wide imports.")
    try:
        return Church.objects.get(church_code__iexact=church_code, is_active=True)
    except Church.DoesNotExist as error:
        raise ValidationError(f"No active church has code {church_code}.") from error


def _jumuiya_for_row(row, church):
    name = row.get("jumuiya", "").strip()
    if not name:
        return None
    try:
        return Jumuiya.objects.get(church=church, name__iexact=name, is_active=True)
    except Jumuiya.DoesNotExist as error:
        raise ValidationError(
            f"No active Jumuiya named {name} exists in {church.church_name}."
        ) from error


def _generated_username(bahasha_number):
    identifier = slugify(bahasha_number).replace("-", "_") or "member"
    base = f"member_{identifier}"[:140]
    candidate = base
    suffix = 1
    while User.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        candidate = f"{base[: 149 - len(str(suffix))]}_{suffix}"
    return candidate


def _member_data(row, request_user):
    full_name = row.get("full_name", "").strip()
    bahasha_number = row.get("bahasha_number", "").strip().upper()
    raw_phone = row.get("phone_number", "").strip()
    if not full_name:
        raise ValidationError("full_name is required.")
    if not bahasha_number:
        raise ValidationError("bahasha_number is required.")
    if not raw_phone:
        raise ValidationError("phone_number is required.")

    phone_code, local_number = split_phone_number(raw_phone)
    church = _church_for_row(row, request_user)
    approval_status = _choice_value(
        row.get("approval_status"),
        Member.APPROVAL_STATUS,
        "approval_status",
        default="APPROVED",
    )
    is_active = _boolean_value(row.get("is_active"), default=True)
    if approval_status != "APPROVED":
        is_active = False

    return {
        "username": _generated_username(bahasha_number),
        "full_name": full_name,
        "phone_number": normalize_phone_number(phone_code, local_number),
        "email": row.get("email", "").strip(),
        "church": church,
        "jumuiya": _jumuiya_for_row(row, church),
        "church_groups": [],
        "bahasha_number": bahasha_number,
        "gender": _choice_value(
            row.get("gender"), Member.GENDER_CHOICES, "gender"
        )
        if row.get("gender", "").strip()
        else "",
        "marital_status": _choice_value(
            row.get("marital_status"),
            Member.MARITAL_STATUS_CHOICES,
            "marital_status",
        )
        if row.get("marital_status", "").strip()
        else "",
        "demographics": row.get("demographics", "").strip(),
        "approval_status": approval_status,
        "is_active": is_active,
    }


def read_member_csv(uploaded_file):
    try:
        content = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise MemberCsvError("The CSV must use UTF-8 encoding.") from error

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise MemberCsvError("The CSV is empty or has no header row.")

    normalized_headers = [_header_name(header) for header in reader.fieldnames]
    if len(normalized_headers) != len(set(normalized_headers)):
        raise MemberCsvError("CSV header names must be unique.")
    missing = sorted(REQUIRED_MEMBER_CSV_HEADERS - set(normalized_headers))
    if missing:
        raise MemberCsvError(f"Missing required columns: {', '.join(missing)}.")

    rows = []
    for raw_row in reader:
        row = {
            normalized: raw_row.get(original, "") or ""
            for original, normalized in zip(reader.fieldnames, normalized_headers)
        }
        if any(value.strip() for value in row.values()):
            rows.append(row)
        if len(rows) > MAX_MEMBER_CSV_ROWS:
            raise MemberCsvError(
                f"The CSV cannot contain more than {MAX_MEMBER_CSV_ROWS:,} rows."
            )
    if not rows:
        raise MemberCsvError("The CSV contains no member rows.")
    return rows


@transaction.atomic
def import_members_csv(uploaded_file, request_user):
    rows = read_member_csv(uploaded_file)
    errors = []
    imported_count = 0
    for row_number, row in enumerate(rows, start=2):
        try:
            create_member(_member_data(row, request_user))
            imported_count += 1
        except (ValidationError, IntegrityError) as error:
            errors.append(
                {
                    "row": row_number,
                    "member": row.get("full_name") or row.get("bahasha_number") or "-",
                    "messages": _error_messages(error),
                }
            )
    if errors:
        raise MemberCsvImportError(errors)
    return MemberCsvImportResult(imported_count=imported_count)


def write_members_csv(file_object, members):
    writer = csv.DictWriter(file_object, fieldnames=MEMBER_CSV_HEADERS)
    writer.writeheader()
    for member in members:
        row = {
            "full_name": member.user.full_name,
            "phone_number": member.user.phone_number,
            "email": member.user.email,
            "church_code": member.church.church_code,
            "jumuiya": member.jumuiya.name if member.jumuiya else "",
            "bahasha_number": member.bahasha_number,
            "gender": member.get_gender_display() if member.gender else "",
            "marital_status": member.get_marital_status_display()
            if member.marital_status
            else "",
            "demographics": member.demographics or "",
            "approval_status": member.get_approval_status_display(),
            "is_active": "Yes" if member.is_active else "No",
        }
        writer.writerow({key: _safe_csv_cell(value) for key, value in row.items()})
