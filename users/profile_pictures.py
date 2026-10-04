import mimetypes

from django import forms
from django.http import FileResponse, Http404


MAX_PROFILE_PICTURE_SIZE = 5 * 1024 * 1024
ALLOWED_PROFILE_PICTURE_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_profile_picture(picture, current_picture=None):
    if not picture or picture == current_picture:
        return picture
    if picture.size > MAX_PROFILE_PICTURE_SIZE:
        raise forms.ValidationError("Profile picture must be 5 MB or smaller.")

    image = getattr(picture, "image", None)
    if getattr(image, "format", "") not in ALLOWED_PROFILE_PICTURE_FORMATS:
        raise forms.ValidationError("Upload a JPEG, PNG, or WebP image.")
    if image.width > 5000 or image.height > 5000:
        raise forms.ValidationError(
            "Image dimensions must not exceed 5000 x 5000 pixels."
        )
    return picture


def profile_picture_response(user):
    picture = user.profile_picture
    if not picture:
        raise Http404("Profile picture not found.")
    try:
        picture_file = picture.open("rb")
    except FileNotFoundError as error:
        raise Http404("Profile picture not found.") from error

    content_type = mimetypes.guess_type(picture.name)[0] or "application/octet-stream"
    response = FileResponse(picture_file, content_type=content_type)
    response["Cache-Control"] = "private, no-store"
    return response
