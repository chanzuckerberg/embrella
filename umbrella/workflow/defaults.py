"""
Effective parameter defaults for a launch.

    schema.yaml default
      < ParameterDefaults rows, least specific first     (processes.models)
      < processor.session_defaults(msi_session)          (e.g. calibrated pixel size)

One resolver, called by the defaults endpoint (what the form shows) and by
PipelineExecutor.prepare (what actually runs), so preview == run.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set

from processes.models import ParameterDefaults, ProcSoftware
from tem.models import MsiSession

from .processors import BaseProcessor

SOURCE_SCHEMA = "schema"
SOURCE_SESSION = "session"


@dataclass
class ResolvedDefaults:
    values: Dict[str, Any] = field(default_factory=dict)
    required: Set[str] = field(default_factory=set)  # keys a row set to null
    sources: Dict[str, str] = field(default_factory=dict)  # key -> "schema" | "row:<pk>" | "session"

    def set(self, key: str, value: Any, source: str) -> None:
        self.values[key] = value
        self.sources[key] = source
        self.required.discard(key)

    def clear(self, key: str, source: str) -> None:
        """A null in a row: drop the default and make the user fill it in."""
        self.values.pop(key, None)
        self.sources[key] = source
        self.required.add(key)

    def merge(self, posted: Dict[str, Any]) -> Dict[str, Any]:
        """Posted values win; defaults fill the gaps."""
        return {**self.values, **posted}

    def missing(self, merged: Dict[str, Any], schema_required: Iterable[str]) -> List[str]:
        """Required keys (schema or cleared) that are still blank after merging."""
        wanted = dict.fromkeys([*schema_required, *sorted(self.required)])
        return [key for key in wanted if _is_blank(merged.get(key))]


def resolve_defaults(
    processor: BaseProcessor,
    *,
    msi_session: Optional[MsiSession] = None,
    software_id: Optional[int] = None,
    scope_id: Optional[int] = None,
    cluster_id: Optional[str] = None,
    exclude_row_pk: Optional[int] = None,
) -> ResolvedDefaults:
    """
    A session supplies scope and software; pass them directly when there is no session
    yet (the admin panel). `exclude_row_pk` answers "what would apply without this row".
    """
    resolved = ResolvedDefaults()

    for key, prop in processor.get_parameter_schema().get("properties", {}).items():
        if "default" in prop:
            resolved.set(key, prop["default"], SOURCE_SCHEMA)

    if msi_session:
        software_id = msi_session.session_plan.software_id
        scope_id = msi_session.session_plan.scope_id

    # Rows are keyed on ProcSoftware; a processor without a DB row has no overrides.
    proc_software = ProcSoftware.objects.filter(processor_class=processor.name, active=True).first()
    if proc_software:
        rows = ParameterDefaults.applicable(
            proc_software,
            software_id=software_id,
            scope_id=scope_id,
            cluster_id=cluster_id or proc_software.default_cluster,
            exclude_pk=exclude_row_pk,
        )
        for row in rows:
            _apply_row(resolved, row)

    # Session-derived values are the most specific: they beat a row's null too.
    if msi_session:
        for key, value in processor.session_defaults(msi_session).items():
            if value is not None:
                resolved.set(key, value, SOURCE_SESSION)

    return resolved


def _apply_row(resolved: ResolvedDefaults, row: ParameterDefaults) -> None:
    source = "row:%d" % row.pk
    for key, value in row.values.items():
        if value is None:
            resolved.clear(key, source)
        else:
            resolved.set(key, value, source)


def _is_blank(value: Any) -> bool:
    return value is None or value == ""


# Strict, unlike BaseProcessor._coerce_to_schema_type: admin input must already be
# the right JSON type. bool is checked before int because bool is an int subclass.
_TYPE_CHECKS = {
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "string": lambda v: isinstance(v, str),
}


def check_value_type(value: Any, prop: Dict[str, Any]) -> Optional[str]:
    """Why `value` doesn't fit the schema property, or None when it does. null always fits."""
    if value is None:
        return None

    expected = prop.get("type")
    check = _TYPE_CHECKS.get(expected)
    if check and not check(value):
        return "expected %s, got %s" % (expected, type(value).__name__)

    allowed = prop.get("enum")
    if allowed and value not in allowed:
        return "must be one of %s" % ", ".join(str(option) for option in allowed)

    return None
