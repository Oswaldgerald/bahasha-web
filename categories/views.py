from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render

from categories.forms import ContributionCategoryForm
from categories.models import ContributionCategory
from web.pagination import paginate_queryset
from web.access import church_admin_required, scope_queryset_to_church


def category_queryset_for_user(user):
    categories = ContributionCategory.objects.select_related("church")
    return scope_queryset_to_church(categories, user)


@church_admin_required
def category_list(request):
    categories = category_queryset_for_user(request.user)
    categories = paginate_queryset(request, categories, per_page=12)

    return render(request, "categories/list.html", {"categories": categories})


@church_admin_required
def category_create(request):
    if request.method == "POST":
        form = ContributionCategoryForm(request.POST, request_user=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Contribution category created successfully.")
            return redirect("web_categories")
    else:
        form = ContributionCategoryForm(request_user=request.user)

    return render(request, "categories/create.html", {"form": form})


@church_admin_required
def category_edit(request, category_id):
    category = get_object_or_404(category_queryset_for_user(request.user), id=category_id)

    if request.method == "POST":
        form = ContributionCategoryForm(
            request.POST,
            instance=category,
            request_user=request.user,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Contribution category updated successfully.")
            return redirect("web_categories")
    else:
        form = ContributionCategoryForm(instance=category, request_user=request.user)

    return render(request, "categories/edit.html", {"form": form, "category": category})
