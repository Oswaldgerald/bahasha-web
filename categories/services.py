from .models import ContributionCategory


DEFAULT_CATEGORY_TEMPLATES = [
    {
        "key": "ahadi",
        "name": "Ahadi",
        "description": "Weekly promise offerings.",
        "icon_key": "hand-heart",
        "theme_color": "#A844B7",
        "frequency": "WEEKLY",
        "display_order": 1,
    },
    {
        "key": "jengo",
        "name": "Jengo",
        "description": "Church building and development contributions.",
        "icon_key": "building-2",
        "theme_color": "#F59E0B",
        "frequency": "SEASONAL",
        "display_order": 2,
    },
    {
        "key": "uwakili",
        "name": "Uwakili",
        "description": "Stewardship contributions.",
        "icon_key": "scale",
        "theme_color": "#5EAE65",
        "frequency": "MONTHLY",
        "display_order": 3,
    },
    {
        "key": "jumuiya",
        "name": "Jumuiya",
        "description": "Small Christian community contributions.",
        "icon_key": "users-round",
        "theme_color": "#3E9DE0",
        "frequency": "WEEKLY",
        "display_order": 4,
    },
    {
        "key": "mavuno",
        "name": "Mavuno",
        "description": "Harvest and thanksgiving contributions.",
        "icon_key": "tractor",
        "theme_color": "#27A69A",
        "frequency": "SEASONAL",
        "display_order": 5,
    },
]


def create_default_categories(church):
    return [
        ContributionCategory.objects.get_or_create(
            church=church,
            key=template["key"],
            defaults=template,
        )[0]
        for template in DEFAULT_CATEGORY_TEMPLATES
    ]
