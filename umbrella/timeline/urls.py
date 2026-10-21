"""URLconf for the timeline API (included under /timeline/)."""

from django.urls import path

from timeline.views import GridTimelineView

urlpatterns = [
    path("v1/grids/<int:grid_id>/", GridTimelineView.as_view(), name="grid-timeline"),
]
