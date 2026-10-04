from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render

from churches.models import Church
from web.forms import ChurchForm


@login_required(login_url="login")
def church_list(request):
    churches = Church.objects.all().order_by("church_name")

    return render(request, "churches/list.html", {"churches": churches})


@login_required(login_url="login")
def church_create(request):
    if request.method == "POST":
        form = ChurchForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Church created successfully.")
            return redirect("web_churches")
    else:
        form = ChurchForm()

    return render(request, "churches/create.html", {"form": form})


@login_required(login_url="login")
def church_edit(request, church_id):
    church = get_object_or_404(Church, id=church_id)

    if request.method == "POST":
        form = ChurchForm(request.POST, instance=church)

        if form.is_valid():
            form.save()
            messages.success(request, "Church updated successfully.")
            return redirect("web_churches")
    else:
        form = ChurchForm(instance=church)

    return render(request, "churches/edit.html", {"form": form, "church": church})
