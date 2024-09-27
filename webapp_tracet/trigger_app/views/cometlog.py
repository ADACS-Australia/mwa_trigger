import django_filters
from django.core.paginator import InvalidPage, Paginator
from django.forms import DateTimeInput
from django.shortcuts import render

from .. import models
from ..models.log import CometLog


class CometLogFilter(django_filters.FilterSet):
    created_filter = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
        widget=DateTimeInput(attrs={"type": "datetime-local"}),
    )

    class Meta:
        model = CometLog
        fields = {
            "created_at",
        }


def comet_log(request):
    f = CometLogFilter(request.GET, queryset=CometLog.objects.all())
    logs = f.qs

    # Paginate
    page = request.GET.get("page", 1)
    paginator = Paginator(logs, 100)
    try:
        logs = paginator.page(page)
    except InvalidPage:
        # if the page contains no results (EmptyPage exception) or
        # the page number is not an integer (PageNotAnInteger exception)
        # return the first page
        logs = paginator.page(1)

    return render(
        request, "trigger_app/cometlog_filter.html", {"filter": f, "page_obj": logs}
    )
