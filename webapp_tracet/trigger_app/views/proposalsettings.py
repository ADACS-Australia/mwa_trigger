import os
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import ListView
from tracet import parse_xml
from trigger_app.utils.utils_update import update_proposal_settings_from_api

from .. import forms, models
from ..models.proposal import ProposalSettings, ProposalSettingsArchive


class ProposalSettingsList(ListView):
    model = models.proposal.ProposalSettings
    ordering = ["priority"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['archived_proposals'] = (
            models.proposal.ProposalSettingsArchive.objects.all()
        )
        return context


@login_required
def proposal_form(request, id=None):
    # grab source type telescope dict
    src_tele = parse_xml.SOURCE_TELESCOPES
    if id:
        proposal = models.proposal.ProposalSettings.objects.get(id=id)

        title = f"Editing Proposal #{id}"
    else:
        proposal = None
        title = "New Proposal"
    if request.POST:
        form = forms.ProjectSettingsForm(request.POST, instance=proposal)
        if form.is_valid():
            saved = form.save()
            # on success, the request is redirected as a GET
            return redirect(proposal_decision_path, id=saved.id)
    else:
        form = forms.ProjectSettingsForm(instance=proposal)
    form.fields["testing"].choices = models.constants.TRIGGER_ON
    return render(
        request,
        "trigger_app/proposal_form.html",
        {"form": form, "src_tele": src_tele, "title": title},
    )


def proposal_decision_path(request, id):

    prop_set = models.proposal.ProposalSettings.objects.get(id=id)

    telescope = prop_set.event_telescope

    # Create decision tree flow diagram
    # Set up mermaid javascript
    mermaid_script = f"""flowchart TD
  A(Event) --> B{{"Have we observed\nthis event before?"}}
  B --> |YES| D{{"Is the new event further away than\nthe repointing limit ({prop_set.repointing_limit} degrees)?"}}
  D --> |YES| R(Repoint)
  D --> |NO| END(Ignore)"""
    if telescope is None:
        mermaid_script += """
  B --> |NO| E{Source type?}"""
    else:
        mermaid_script += f"""
  B --> |NO| C{{Is Event from {telescope}?}}
  C --> |NO| END
  C --> |YES| E{{Source type?}}"""
    mermaid_script += """
  E --> F[GRB]"""
    if prop_set.source_type == "GRB":
        mermaid_script += f"""
  F --> J{{"Fermi GRB probability > {prop_set.fermi_prob}\\nor\\nSWIFT Rate_signif > {prop_set.swift_rate_signf} sigma"}}"""
        if prop_set.event_any_duration:
            mermaid_script += f"""
  J --> |YES| L[Trigger Observation]
subgraph GRB
  J
  L
end"""
        else:
            mermaid_script += f"""
  J --> |YES| K{{"Event duration between\n {prop_set.event_min_duration} and {prop_set.event_max_duration} s"}}
  J --> |NO| END
  K --> |YES| L[Trigger Observation]
  K --> |NO| M{{"Event duration between\n{prop_set.pending_min_duration_1} and {prop_set.pending_max_duration_1} s\nor\n{prop_set.pending_min_duration_2} and {prop_set.pending_max_duration_2} s"}}
  M --> |YES| N[Pending a human's decision]
  M --> |NO| END
subgraph GRB
  J
  K
  L
  M
  N
end
  style N fill:orange,color:white"""
    else:
        mermaid_script += """
  F[GRB] --> END"""
    if prop_set.source_type == "FS":
        mermaid_script += f"""
  E --> G[Flare Star] --> L[Trigger Observation]"""
    else:
        mermaid_script += """
  E --> G[Flare Star] --> END"""
    if prop_set.source_type == "NU":
        mermaid_script += f"""
  E --> I[Neutrino]
  I[Neutrino] --> |Antares Event| RANK{{Is the Antares ranking less than or equal to {prop_set.antares_min_ranking}?}}
  RANK --> |YES| L[Trigger Observation]
  RANK --> |NO| END
  I[Neutrino] --> |Non-Antares Event| L[Trigger Observation]
subgraph NU
  I
  RANK
end"""
    else:
        mermaid_script += """
    E --> I[Neutrino] --> END"""
    if prop_set.source_type == "GW":
        mermaid_script += f"""
    E --> H[GW] --> L[Trigger Observation]"""
    else:
        mermaid_script += f"""
    E --> H[GW] --> END"""
    mermaid_script += """
  style A fill:blue,color:white
  style END fill:red,color:white
  style L fill:green,color:white
  style R fill:#21B6A8,color:white"""

    return render(
        request,
        "trigger_app/proposal_decision_path.html",
        {"proposal": prop_set, "mermaid_script": mermaid_script},
    )


@login_required
def update_all_proposals(request):

    update_proposal_settings_from_api()
    print("Updating proposals")
    # return redirect(reverse('proposal_settings'))
    return redirect('proposal_settings')


@login_required
def code_browser(request):
    # Get the path from query parameters
    relative_path = request.GET.get('path', '')

    # Define the root directory
    code_dir = os.path.join('/')

    # Combine with the relative path
    target_dir = os.path.join(code_dir, relative_path.lstrip('/'))

    print(target_dir)

    # Get list of files and directories
    files = []
    if os.path.exists(target_dir):
        for root, dirs, filenames in os.walk(target_dir):
            rel_path = os.path.relpath(root, target_dir)
            if rel_path == '.':
                rel_path = ''

            for filename in filenames:
                if filename.endswith('.py'):  # Only show Python files
                    file_path = os.path.join(rel_path, filename)
                    files.append(file_path)

    return render(
        request,
        'trigger_app/code_browser.html',
        {
            'files': sorted(files),
            'current_path': relative_path,
            'target_dir': target_dir,
        },
    )


@login_required
def view_code_file(request, file_path):
    target_dir = request.GET.get('target_dir', '/')

    # Ensure the file path is within our allowed directory
    full_path = os.path.join(target_dir, file_path)
    file_path = file_path.lstrip('/')

    print(full_path)

    # Basic security check to prevent directory traversal
    if not os.path.commonpath([full_path, '/']) == '/':
        raise Http404("File not found")

    try:
        with open(full_path, 'r') as file:
            content = file.read()
    except FileNotFoundError:
        raise Http404("File not found")

    return render(
        request,
        'trigger_app/view_code.html',
        {'file_path': file_path, 'content': content, 'target_dir': target_dir},
    )


def proposal_stats(request, proposal_id):
    duration = request.GET.get('duration', '0')  # Default to All time
    proposal = ProposalSettings.objects.get(id=proposal_id)

    if duration == '0':  # All time
        stats = proposal.get_decision_statistics_for_duration()
    else:
        # Convert duration to integer months
        months = int(duration)
        stats = proposal.get_decision_statistics_for_duration(months)

    return JsonResponse(stats)


def archived_proposal_stats(request, proposal_id_version):
    try:
        duration = request.GET.get('duration', '0')  # Default to All time
        # Filter by both id and version
        proposal = ProposalSettingsArchive.objects.get(id_version=proposal_id_version)

        if duration == '0':  # All time
            stats = proposal.get_decision_statistics_all_time()
        else:
            # Convert duration to integer months
            months = int(duration)
            stats = proposal.get_decision_statistics_for_duration(months)

        return JsonResponse(stats)

    except ObjectDoesNotExist:
        return JsonResponse(
            {'error': f'Proposal not found with id {proposal_id_version}'},
            status=404,
        )
    except MultipleObjectsReturned:
        return JsonResponse(
            {'error': 'Multiple proposals found. Please specify a version.'}, status=400
        )
    except Exception as e:
        print(f"Error fetching archived proposal stats: {e}")
        return JsonResponse({'error': str(e)}, status=500)
