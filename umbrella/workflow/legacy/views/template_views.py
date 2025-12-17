"""
Template rendering views for workflow UI pages.

These views render legacy Django template-based workflow pages.
They are being kept during the transition to Next.js frontend.
"""

from django.shortcuts import render


def custom_workflow_page(request):
    """Render main workflow page."""
    return render(request, "workflows/workflow_page.html")


def custom_run_workflow_page(request):
    """Render workflow run page."""
    return render(request, "workflows/workflow_run.html")


def cutom_run_denoise_workflow_page(request):
    """Render denoise workflow run page."""
    return render(request, "workflows/workflow_denoise_run.html")


def cutom_run_create_and_import_copick_page(request):
    """Render Copick workflow page."""
    return render(request, "workflows/workflow_copick.html")


def custom_run_membraneseg_page(request):
    """Render membrane segmentation workflow page."""
    return render(request, "workflows/workflow_membraneseg.html")


def custom_run_octopi_page(request):
    """Render Octopi workflow page."""
    return render(request, "workflows/workflow_octopi.html")


def custom_workflow_cancel(request):
    """Render workflow cancel page."""
    return render(request, "workflows/workflow_cancel.html")


def custom_workflow_track(request):
    """Render workflow tracking page."""
    return render(request, "workflows/workflow_track.html")


def custom_workflow_logs(request):
    """Render workflow logs page."""
    return render(request, "workflows/workflow_logs.html")
