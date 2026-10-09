import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models
from django.utils.text import slugify


DEFAULT_CATEGORIES = [
    ("ahadi", "Ahadi", "Weekly promise offerings.", "hand-heart", "#A844B7", "WEEKLY", 1),
    ("jengo", "Jengo", "Church building and development contributions.", "building-2", "#F59E0B", "SEASONAL", 2),
    ("uwakili", "Uwakili", "Stewardship contributions.", "scale", "#5EAE65", "MONTHLY", 3),
    ("jumuiya", "Jumuiya", "Small Christian community contributions.", "users-round", "#3E9DE0", "WEEKLY", 4),
    ("mavuno", "Mavuno", "Harvest and thanksgiving contributions.", "tractor", "#27A69A", "SEASONAL", 5),
]


def scope_existing_categories(apps, schema_editor):
    Category = apps.get_model("categories", "ContributionCategory")
    Church = apps.get_model("churches", "Church")
    Contribution = apps.get_model("contributions", "Contribution")
    AnnualTarget = apps.get_model("annual_targets", "MemberAnnualTarget")
    ExcelUpload = apps.get_model("excel_uploads", "ExcelUpload")

    church_ids = list(Church.objects.order_by("id").values_list("id", flat=True))
    original_categories = list(Category.objects.order_by("id"))
    if original_categories and not church_ids:
        raise RuntimeError("Create a church before migrating existing contribution categories.")

    used_keys = set()
    for original in original_categories:
        base_key = slugify(original.code or original.name) or f"category-{original.id}"
        key = base_key
        suffix = 2
        while key in used_keys:
            key = f"{base_key}-{suffix}"
            suffix += 1
        used_keys.add(key)

        original.church_id = church_ids[0]
        original.key = key
        original.public_id = uuid.uuid4()
        original.save(update_fields=["church", "key", "public_id"])

        categories_by_church = {church_ids[0]: original}
        for church_id in church_ids[1:]:
            categories_by_church[church_id] = Category.objects.create(
                public_id=uuid.uuid4(),
                church_id=church_id,
                name=original.name,
                name_sw=original.name_sw,
                key=key,
                code=original.code,
                description=original.description,
                frequency=original.frequency,
                display_order=original.display_order,
                is_annual=original.is_annual,
                icon_key=original.icon_key,
                theme_color=original.theme_color,
                suggested_amount=original.suggested_amount,
                minimum_amount=original.minimum_amount,
                maximum_amount=original.maximum_amount,
                is_mobile_visible=original.is_mobile_visible,
                allows_member_payment=original.allows_member_payment,
                allows_catch_up=original.allows_catch_up,
                is_active=original.is_active,
            )

        for church_id, scoped_category in categories_by_church.items():
            Contribution.objects.filter(
                category_id=original.id,
                church_id=church_id,
            ).update(category_id=scoped_category.id)
            AnnualTarget.objects.filter(
                category_id=original.id,
                church_id=church_id,
            ).update(category_id=scoped_category.id)
            ExcelUpload.objects.filter(
                selected_category_id=original.id,
                church_id=church_id,
            ).update(selected_category_id=scoped_category.id)

    for church_id in church_ids:
        existing_keys = set(
            Category.objects.filter(church_id=church_id).values_list("key", flat=True)
        )
        for key, name, description, icon, color, frequency, order in DEFAULT_CATEGORIES:
            if key in existing_keys:
                continue
            Category.objects.create(
                public_id=uuid.uuid4(),
                church_id=church_id,
                key=key,
                name=name,
                description=description,
                icon_key=icon,
                theme_color=color,
                frequency=frequency,
                display_order=order,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("categories", "0002_alter_contributioncategory_options_and_more"),
        ("churches", "0002_churchgroup"),
        ("contributions", "0002_contribution_contribution_amount_positive"),
        ("annual_targets", "0001_initial"),
        ("excel_uploads", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="contributioncategory",
            name="public_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="contributioncategory",
            name="church",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="contribution_categories",
                to="churches.church",
            ),
        ),
        migrations.AddField(
            model_name="contributioncategory",
            name="name_sw",
            field=models.CharField(blank=True, default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="contributioncategory",
            name="key",
            field=models.SlugField(default="", max_length=80),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="contributioncategory",
            name="icon_key",
            field=models.CharField(
                choices=[
                    ("hand-heart", "Hand and heart"),
                    ("landmark", "Church building"),
                    ("scale", "Scale"),
                    ("users-round", "Community"),
                    ("tractor", "Harvest"),
                    ("gift", "Gift"),
                    ("heart-handshake", "Partnership"),
                    ("badge-dollar-sign", "Fund"),
                    ("building-2", "Building project"),
                ],
                default="hand-heart",
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="contributioncategory",
            name="theme_color",
            field=models.CharField(
                default="#2D1B69",
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Enter a six-digit hex color such as #2D1B69.",
                        regex="^#[0-9A-Fa-f]{6}$",
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="contributioncategory",
            name="suggested_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="contributioncategory",
            name="minimum_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="contributioncategory",
            name="maximum_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="contributioncategory",
            name="is_mobile_visible",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="contributioncategory",
            name="allows_member_payment",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="contributioncategory",
            name="allows_catch_up",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="contributioncategory",
            name="name",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="contributioncategory",
            name="code",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.RunPython(scope_existing_categories, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="contributioncategory",
            name="church",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="contribution_categories",
                to="churches.church",
            ),
        ),
        migrations.AlterField(
            model_name="contributioncategory",
            name="public_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddConstraint(
            model_name="contributioncategory",
            constraint=models.UniqueConstraint(
                fields=("church", "key"),
                name="unique_category_key_per_church",
            ),
        ),
        migrations.AddConstraint(
            model_name="contributioncategory",
            constraint=models.UniqueConstraint(
                fields=("church", "name"),
                name="unique_category_name_per_church",
            ),
        ),
        migrations.AddConstraint(
            model_name="contributioncategory",
            constraint=models.UniqueConstraint(
                fields=("church", "code"),
                name="unique_category_code_per_church",
            ),
        ),
        migrations.AddIndex(
            model_name="contributioncategory",
            index=models.Index(
                fields=["church", "is_active", "is_mobile_visible"],
                name="category_mobile_lookup",
            ),
        ),
    ]
