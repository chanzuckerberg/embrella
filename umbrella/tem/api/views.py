"""
API views for TEM session management.

Contains API endpoints for querying MSI sessions and their associated
processing runs and tomograms.
"""
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from processes.models import ReviewTomogram
from tem.models import MsiSession


@method_decorator(csrf_exempt, name='dispatch')
class SessionView(View):
    """
    View to handle both /api/sessions and /api/sessions/{session_id} endpoints.

    Provides access to MSI session data including associated processing runs
    and tomogram counts.
    """

    def get_session_data(self, session):
        """
        Get formatted session data with runs and tomogram counts.

        Args:
            session: MsiSession instance

        Returns:
            Dictionary with session metadata and runs list
        """
        runs_data = []
        seen_runs = set()

        # only runs that belong to plans we want to expose here
        proc_runs = session.procrun_set.filter(
            proc_plan__name__in=['czii-live', 'czii-denoise'],
        ).select_related('proc_plan')

        for proc_run in proc_runs:
            # Count tomograms grouped by reconstruction_type
            review_data = ReviewTomogram.objects.filter(
                run_id=proc_run.name, session=session,
            ).values('reconstruction_type').annotate(
                tomogram_count=Count('tomogram_id', distinct=True),
            )
            tomogram_counts = {
                d['reconstruction_type']: d['tomogram_count'] for d in review_data
            }

            # choose recon types based on plan
            if proc_run.proc_plan.name == 'czii-live':
                reconstruction_types = [
                    {'type': 'DCTF',   'job_name': 'aretomo3',
                        'vol_number': 'vol001'},
                    {'type': 'SART',   'job_name': 'aretomo3',
                        'vol_number': 'vol003'},
                ]
            elif proc_run.proc_plan.name == 'czii-denoise':
                # NOTE: denoise does not have a volume number
                reconstruction_types = [
                    {'type': 'Denoised', 'job_name': 'denoise', 'vol_number': ''},
                ]
            else:
                # skip other plans (e.g., czii-copick)
                continue

            for recon_info in reconstruction_types:
                recon_type = recon_info['type']
                run_key = f"{proc_run.name}_{recon_type}"
                if run_key in seen_runs:
                    continue
                seen_runs.add(run_key)

                save_path = (
                    f"/hpc/group.czii/krios1.processing/project/"
                    f"{recon_info['job_name']}/{session.name}/{proc_run.name}"
                )
                if recon_info['vol_number']:
                    save_path += f"/{recon_info['vol_number']}"
                runs_data.append({
                    "runId": proc_run.name,
                    "numTomograms": tomogram_counts.get(recon_type, 0),
                    "reconstructionType": recon_type,
                    "savePath": save_path,
                })

        return {
            "sessionId": session.id,
            "sessionName": session.name,
            "createdAt": session.created_at.isoformat() if session.created_at else None,
            "projectName": session.project.name if session.project else None,
            "runs": runs_data,
        }

    def get(self, request, session_id=None):
        """
        Handle GET requests for both endpoints:
        - /api/sessions/ (list all sessions)
        - /api/sessions/{session_id} (get specific session)
        """
        try:
            if session_id:
                # Get specific session
                try:
                    session = MsiSession.objects.select_related(
                        'project').get(name=session_id)
                except MsiSession.DoesNotExist:
                    return JsonResponse({"error": "Session not found"}, status=404)

                session_data = self.get_session_data(session)
                return JsonResponse(session_data, safe=False)

            else:
                # List all sessions
                search = request.GET.get('search', '').strip()

                # Start with base queryset
                sessions_qs = MsiSession.objects.select_related(
                    'project',
                ).prefetch_related(
                    'procrun_set',
                )

                # Apply search filter if provided
                if search:
                    sessions_qs = sessions_qs.filter(
                        Q(name__icontains=search) |
                        Q(project__name__icontains=search),
                    )

                # Get all sessions
                sessions = sessions_qs.order_by('-created_at')

                # Get data for each session
                sessions_data = []
                for session in sessions:
                    session_data = self.get_session_data(session)
                    # Include session if it has any runs (regardless of tomogram count)
                    if session_data["runs"]:
                        sessions_data.append(session_data)

                return JsonResponse(sessions_data, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
