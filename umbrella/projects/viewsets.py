"""DRF ViewSets for projects and their members.

Any authenticated user can read projects and create one (becoming its EDITOR).
Updating, deleting and managing members needs ``services.can_manage``: staff,
the project leader, or an EDITOR member.
"""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response

from projects import services
from projects.models import Project, ProjectMembership, ProjectRole
from projects.serializers import MemberWriteSerializer, ProjectMemberSerializer, ProjectSerializer

LEADER_ROLE_ERROR = "The project leader must stay an editor. Change the leader first."

# Swagger section grouping every project endpoint.
PROJECTS_TAG = "Projects"

# Who may write; repeated in each write endpoint's docs.
MANAGE_NOTE = "Requires staff, the project leader, or an `editor` member."


class CanManageProject(BasePermission):
    message = "Only staff, the project leader, or project editors can change this project."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return services.can_manage(request.user, obj)


@extend_schema_view(
    list=extend_schema(
        tags=[PROJECTS_TAG],
        summary="List projects",
        description=(
            "Return every project, ordered by name. Each entry nests its members "
            "(`{user_id, username, role}`), institutions and contributors."
        ),
    ),
    retrieve=extend_schema(
        tags=[PROJECTS_TAG],
        summary="Get a project",
        description="Return one project with members, institutions and contributors nested.",
    ),
    create=extend_schema(
        tags=[PROJECTS_TAG],
        summary="Create a project",
        description=(
            "Any authenticated user may create a project and becomes an `editor`. "
            "The `project_leader`, if set, is also made an `editor`. "
            "Set institutions and contributors with `institution_ids` / `contributor_ids`. "
            "`name` must be unique."
        ),
    ),
    update=extend_schema(
        tags=[PROJECTS_TAG],
        summary="Replace a project",
        description=f"Replace all writable fields. Members change only via `members/`. {MANAGE_NOTE}",
    ),
    partial_update=extend_schema(
        tags=[PROJECTS_TAG],
        summary="Update a project",
        description=(
            'Update the given fields, e.g. `{"institution_ids": [1, 2]}`. '
            f"Members change only via `members/`. {MANAGE_NOTE}"
        ),
    ),
    destroy=extend_schema(
        tags=[PROJECTS_TAG],
        summary="Delete a project",
        description=f"Delete the project, its memberships and its role groups. {MANAGE_NOTE}",
    ),
)
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
        methods=["GET"],
        tags=[PROJECTS_TAG],
        summary="List project members",
        description="Return the project's members with their role, ordered by username.",
        responses=ProjectMemberSerializer(many=True),
    )
    @extend_schema(
        methods=["POST"],
        tags=[PROJECTS_TAG],
        summary="Add a project member",
        description=(
            f"Add `user` with `role` (`viewer` by default), or update the role if already a member. {MANAGE_NOTE}"
        ),
        request=MemberWriteSerializer,
        responses={status.HTTP_201_CREATED: ProjectMemberSerializer},
    )
    @extend_schema(
        methods=["PATCH"],
        tags=[PROJECTS_TAG],
        summary="Change a member's role",
        description=f"Set an existing member's `role`. The project leader must stay `editor`. {MANAGE_NOTE}",
        request=MemberWriteSerializer,
        responses=ProjectMemberSerializer,
    )
    @extend_schema(
        methods=["DELETE"],
        tags=[PROJECTS_TAG],
        summary="Remove a project member",
        description=f"Remove `user` from the project. The project leader can't be removed. {MANAGE_NOTE}",
        request=MemberWriteSerializer,
        responses={status.HTTP_204_NO_CONTENT: None},
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
