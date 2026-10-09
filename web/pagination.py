from django.core.paginator import Paginator


DEFAULT_PAGE_SIZE = 20


def paginate_queryset(
    request,
    queryset,
    per_page=DEFAULT_PAGE_SIZE,
    page_parameter="page",
):
    return Paginator(queryset, per_page).get_page(request.GET.get(page_parameter))
