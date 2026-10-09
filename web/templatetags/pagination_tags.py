from django import template


register = template.Library()


@register.inclusion_tag("partials/pagination.html", takes_context=True)
def render_pagination(context, page_obj):
    request = context["request"]
    query = request.GET.copy()
    query.pop("page", None)
    return {
        "page_obj": page_obj,
        "page_numbers": page_obj.paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=1,
            on_ends=1,
        ),
        "query_string": query.urlencode(),
    }
