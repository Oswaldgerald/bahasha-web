from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Member

# Create your views here.
@login_required(login_url="login")
def member_card(request, member_id):
    member = get_object_or_404(
        Member.objects.select_related(
            "user",
            "church",
            "jumuiya"
        ),
        id=member_id
    )

    return render(request, "members/card.html", {
        "member": member
    })