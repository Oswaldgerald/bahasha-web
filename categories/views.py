from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render

from categories.models import ContributionCategory
from web.forms import ContributionCategoryForm


@login_required(login_url="login")
def category_list(request):
    categories = ContributionCategory.objects.all()

    return render(request, "categories/list.html", {"categories": categories})


@login_required(login_url="login")
def category_create(request):
    if request.method == "POST":
        form = ContributionCategoryForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Contribution category created successfully.")
            return redirect("web_categories")
    else:
        form = ContributionCategoryForm()

    return render(request, "categories/create.html", {"form": form})


@login_required(login_url="login")
def category_edit(request, category_id):
    category = get_object_or_404(ContributionCategory, id=category_id)

    if request.method == "POST":
        form = ContributionCategoryForm(request.POST, instance=category)

        if form.is_valid():
            form.save()
            messages.success(request, "Contribution category updated successfully.")
            return redirect("web_categories")
    else:
        form = ContributionCategoryForm(instance=category)

    return render(request, "categories/edit.html", {"form": form, "category": category})
