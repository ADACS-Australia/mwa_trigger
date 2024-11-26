"""webapp_tracet URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import TemplateView
from trigger_app.views import (
    cometlog,
    event,
    eventgroup,
    homepage,
    observations,
    proposal,
    proposalsettings,
    user,
)
from trigger_app.views.proposalsettings import update_all_proposals

from webapp_tracet.api import api

# from trigger_app.api import app


urlpatterns = [
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", homepage.home_page),
    path("user_alert_status/", user.user_alert_status),
    path("user_alert_delete/<int:id>/", user.user_alert_delete),
    path("user_alert_create/", user.user_alert_create),
    path("event_group_log/", eventgroup.EventGroupList),
    path("test_event_group_log/", eventgroup.TestEventGroupList),
    path("event_group_details/<int:tid>/", eventgroup.EventGroup_details),
    path("event_log/", event.EventList),
    path("test_event_log/", event.TestEventList),
    path("comet_log/", cometlog.comet_log),
    path(
        "proposal_settings/",
        proposalsettings.ProposalSettingsList.as_view(),
        name='proposal_settings',
    ),
    path("proposal_create/", proposalsettings.proposal_form),
    path("proposal_edit/<int:id>/", proposalsettings.proposal_form),
    path("proposal_decision_path/<int:id>/", proposalsettings.proposal_decision_path),
    path("proposal_decision_details/<int:id>/", proposal.ProposalDecision_details),
    path(
        "proposal_decision_result/<int:id>/<int:decision>/",
        proposal.ProposalDecision_result,
    ),
    path("proposal_decision_log/", proposal.ProposalDecisionList),
    path("observation_mwa_response/<str:id>/", observations.MWAResponse),
    path("cancel_atca_observation/<str:id>/", observations.cancel_atca_observation),
    path("voevent_view/<int:id>/", event.voevent_view),
    path("event_create/", event.event_create),
    path("test_upload_xml/", event.test_upload_xml),
    path("api/", api.urls),
    path('update_all_proposals/', update_all_proposals, name='update_all_proposals'),
    path("code-browser/", proposalsettings.code_browser, name='code_browser'),
    path(
        "code-browser/<path:file_path>",
        proposalsettings.view_code_file,
        name='view_code_file',
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
