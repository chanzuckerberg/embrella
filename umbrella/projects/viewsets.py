"""DRF ViewSets for projects and their members.

Any authenticated user can read projects and create one (becoming its EDITOR).
Updating, deleting and managing members needs ``services.can_manage``: staff,
the project leader, or an EDITOR member.
"""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response

from projects import services
from projects.models import Project, ProjectMembership, ProjectRole
from projects.serializers import MemberWriteSerializer, ProjectMemberSerializer, ProjectSerializer

LEADER_ROLE_ERROR = "The project leader must stay an editor. Change the leader first."


class CanManageProject(BasePermission):
    message = "Only staff, the project leader, or project editors can change this project."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return services.can_manage(request.user, obj)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = (
        Project.objects.select_related("project_leader", "documentation_space")
        .prefetch_related("memberships__user", "institutions", "contributors__institution")
        .order_by("name")
    )
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, CanManageProject]

    def perform_create(self, serializer):
        project = serializer.save()
        services.add_member(project, self.request.user, ProjectRole.EDITOR)

    @extend_schema(
        summary="List or change project members",
        description=(
            "GET lists members. POST `{user, role}` adds a member (or updates their role). "
            "PATCH `{user, role}` changes a member's role. DELETE `{user}` removes a member. "
            "The project leader always stays an editor."
        ),
        request=MemberWriteSerializer,
        responses=ProjectMemberSerializer(many=True),
    )
    @action(detail=True, methods=["get", "post", "patch", "delete"])
    def members(self, request, pk=None):
        project = self.get_object()

        if request.method == "GET":
            memberships = project.memberships.select_related("user").order_by("user__username")
            return Response(ProjectMemberSerializer(memberships, many=True).data)

        payload = MemberWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        user = payload.validated_data["user"]
        role = ProjectRole(payload.validated_data["role"])

        # The leader is re-added as editor on every save; refuse changes that would be undone.
        is_leader = user.id == project.project_leader_id
        if is_leader and (request.method == "DELETE" or role != ProjectRole.EDITOR):
            return Response({"detail": LEADER_ROLE_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "DELETE":
            services.remove_member(project, user)
            return Response(status=status.HTTP_204_NO_CONTENT)

        if request.method == "PATCH":
            membership = get_object_or_404(ProjectMembership, project=project, user=user)
            services.set_role(membership, role)
            return Response(ProjectMemberSerializer(membership).data)

        membership = services.add_member(project, user, role)
        return Response(ProjectMemberSerializer(membership).data, status=status.HTTP_201_CREATED)
