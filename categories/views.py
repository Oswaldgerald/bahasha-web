from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render

from categories.forms import ContributionCategoryForm
from categories.models import ContributionCategory


def category_queryset_for_user(user):
    categories = ContributionCategory.objects.select_related("church")
    if not user.is_superuser:
        if not user.church_id:
            return categories.none()
        categories = categories.filter(church_id=user.church_id)
    return categories


@login_required(login_url="login")
def category_list(request):
    categories = category_queryset_for_user(request.user)

    return render(request, "categories/list.html", {"categories": categories})


@login_required(login_url="login")
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


@login_required(login_url="login")
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
