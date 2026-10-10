from django.core import signing

from api.common.errors import ApiError


CURSOR_SALT = "bahasha-api-v1-cursor"
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50


def decode_cursor(cursor):
    if not cursor:
        return 0
    try:
        payload = signing.loads(cursor, salt=CURSOR_SALT, max_age=86400)
        offset = int(payload["offset"])
    except (signing.BadSignature, KeyError, TypeError, ValueError) as error:
        raise ApiError(
            "VALIDATION_ERROR",
            "The pagination cursor is invalid or expired.",
            status=422,
            fields={"cursor": ["Enter a valid cursor."]},
        ) from error
    if offset < 0:
        raise ApiError(
            "VALIDATION_ERROR",
            "The pagination cursor is invalid.",
            status=422,
            fields={"cursor": ["Enter a valid cursor."]},
        )
    return offset


def paginate(sequence, *, cursor=None, page_size=DEFAULT_PAGE_SIZE):
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise ApiError(
            "VALIDATION_ERROR",
            f"page_size must be between 1 and {MAX_PAGE_SIZE}.",
            status=422,
            fields={"page_size": [f"Use a value from 1 to {MAX_PAGE_SIZE}."]},
        )

    offset = decode_cursor(cursor)
    values = list(sequence[offset : offset + page_size + 1])
    has_more = len(values) > page_size
    items = values[:page_size]
    next_cursor = None
    if has_more:
        next_cursor = signing.dumps(
            {"offset": offset + page_size},
            salt=CURSOR_SALT,
            compress=True,
        )
    return items, {"next_cursor": next_cursor, "has_more": has_more}
