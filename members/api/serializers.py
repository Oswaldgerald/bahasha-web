def named_reference(instance):
    if not instance:
        return None
    return {"id": instance.public_id, "name": instance.name}


def member_payload(member):
    user = member.user
    return {
        "id": member.public_id,
        "full_name": user.full_name,
        "username": user.username,
        "email": user.email,
        "phone_number": user.phone_number,
        "bahasha_number": member.bahasha_number,
        "gender": member.gender.lower() if member.gender else None,
        "marital_status": (
            member.marital_status.lower() if member.marital_status else None
        ),
        "approval_status": member.approval_status.lower(),
        "photo_url": "/api/v1/me/photo" if user.profile_picture else None,
        "church": {
            "id": member.church.public_id,
            "code": member.church.church_code,
            "name": member.church.church_name,
        },
        "jumuiya": named_reference(member.jumuiya),
        "church_groups": [
            named_reference(group) for group in member.church_groups.all()
        ],
    }
