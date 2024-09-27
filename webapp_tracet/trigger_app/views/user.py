from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render

from ..forms import UserAlertForm
from ..models.alert import AlertPermission, UserAlerts
from ..models.proposal import ProposalSettings


@login_required
def user_alert_status(request):

    proposals = ProposalSettings.objects.all()

    prop_alert_list = []
    for prop in proposals:
        # For each proposals find the user and admin alerts
        u = request.user
        user_alerts = UserAlerts.objects.filter(user=u, proposal=prop)
        alert_permissions = AlertPermission.objects.get(user=u, proposal=prop)
        # Put them into a dict that can be looped over in the html
        prop_alert_list.append(
            {
                "proposal": prop,
                "user": user_alerts,
                "permission": alert_permissions,
            }
        )
    return render(
        request,
        "trigger_app/user_alert_status.html",
        {"prop_alert_list": prop_alert_list},
    )


@login_required
def user_alert_delete(request, id):
    u = request.user
    user_alert = UserAlerts.objects.get(user=u, id=id)
    user_alert.delete()
    return HttpResponseRedirect("/user_alert_status/")


@login_required
def user_alert_create(request):
    if request.POST:
        # Create UserAlert that already includes user and proposal
        u = request.user
        ua = UserAlerts(user=u)
        # Let user update everything else
        form = UserAlertForm(request.POST, instance=ua)
        if form.is_valid():
            try:
                form.save()
                # on success, the request is redirected as a GET
                return HttpResponseRedirect("/user_alert_status/")
            except:
                pass  # handling can go here
    else:
        form = UserAlertForm()
    return render(request, "trigger_app/form.html", {"form": form})

