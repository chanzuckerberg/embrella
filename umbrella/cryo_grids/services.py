"""
Service layer for cryo_grids operations that need to be shared across
ViewSets / views and are non-trivial enough to warrant isolation from
HTTP-handling code.
"""

from django.db import transaction

from cryo_grids.models import CryoGrid, CryoGridBox, GridLabel


class DuplicateGridError(Exception):
    """Raised when a grid duplication request cannot be satisfied."""


def get_available_positions(box: CryoGridBox) -> list[int]:
    """Return sorted list of 1-indexed positions in ``box`` not occupied by a non-trashed grid."""
    max_grids = box.max_grids or 4
    used = set(CryoGrid.objects.filter(grid_box=box, trashed=False).values_list("position_in_box", flat=True))
    return sorted(set(range(1, max_grids + 1)) - used)


@transaction.atomic
def duplicate_grid(
    *,
    source_grid: CryoGrid,
    destination_box: CryoGridBox,
    number_to_copy: int,
    request_user,
) -> list[CryoGrid]:
    """Duplicate ``source_grid`` into ``destination_box`` ``number_to_copy`` times.

    Wrapped in a transaction so partial failures roll back.
    """
    if source_grid.trashed:
        raise DuplicateGridError("Cannot duplicate a trashed grid.")
    if number_to_copy < 1:
        raise DuplicateGridError("number_to_copy must be at least 1.")

    # Lock the destination box's grids to prevent concurrent position allocation.
    locked_used = set(
        CryoGrid.objects.select_for_update()
        .filter(grid_box=destination_box, trashed=False)
        .values_list("position_in_box", flat=True)
    )
    max_grids = destination_box.max_grids or 4
    available_positions = sorted(set(range(1, max_grids + 1)) - locked_used)

    if len(available_positions) < number_to_copy:
        raise DuplicateGridError(
            f'Box "{destination_box}" has only {len(available_positions)} available position(s); '
            f"cannot fit {number_to_copy} more grid(s)."
        )

    # Lock the sibling-copy set to make `max(copy_number) + 1` race-free.
    locked_copy_numbers = list(
        CryoGrid.objects.select_for_update()
        .filter(
            name=source_grid.name,
            freezing_session=source_grid.freezing_session,
            specimen=source_grid.specimen,
        )
        .values_list("copy_number", flat=True)
    )
    next_copy_number = (max(locked_copy_numbers) if locked_copy_numbers else 0) + 1

    created: list[CryoGrid] = []
    for i in range(number_to_copy):
        new_grid = CryoGrid.objects.get(id=source_grid.id)
        new_grid.pk = None
        new_grid.grid_cassette = None
        new_grid.slot_number_in_cassette = None
        new_grid.trashed = False
        new_grid.grid_box = destination_box
        new_grid.position_in_box = available_positions[i]
        new_grid.copy_number = next_copy_number + i
        new_grid.save()

        for gl in GridLabel.objects.filter(grid=source_grid):
            GridLabel.objects.create(grid=new_grid, label=gl.label, added_by=request_user)

        created.append(new_grid)

    return created
