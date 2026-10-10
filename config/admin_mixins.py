from django.urls import reverse
from django.utils.html import format_html


class RowDeleteActionMixin:
    """Expose Django's protected delete confirmation from each admin list row."""

    def get_list_display(self, request):
        list_display = tuple(super().get_list_display(request))

        if not self.has_delete_permission(request):
            return list_display

        def delete_record(obj):
            if not self.has_delete_permission(request, obj):
                return ""

            delete_url = reverse(
                f"admin:{obj._meta.app_label}_{obj._meta.model_name}_delete",
                args=(obj.pk,),
            )
            return format_html(
                '<a class="admin-row-delete" href="{}" '
                'aria-label="Delete {}" title="Delete">'
                '<i data-lucide="trash-2" aria-hidden="true"></i>'
                '<span>Delete</span></a>',
                delete_url,
                obj,
            )

        delete_record.short_description = "Delete"
        return (*list_display, delete_record)
