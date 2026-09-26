# from django.contrib.auth.decorators import login_required
# from django.shortcuts import get_object_or_404, render

# from members.models import Member


# @login_required(login_url="login")
# def member_card(request, member_id):
#     member = get_object_or_404(
#         Member.objects.select_related(
#             "church",
#             "user",
#             "jumuiya",
#         ),
#         id=member_id,
#     )

#     return render(
#         request,
#         "printing/member_card.html",
#         {
#             "member": member,
#         },
#     )