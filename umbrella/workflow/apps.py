"""
Workflow App Configuration

Handles automatic synchronization of processor metadata to database on server startup.
"""

import logging

from django.apps import AppConfig
from django.db import transaction

logger = logging.getLogger(__name__)

OPERATOR_OWNED_FIELDS = frozenset({"script_directory"})


class WorkflowConfig(AppConfig):
    """
    AppConfig for the workflow application.

    Automatically syncs processor metadata to database on server startup,
    eliminating the need for manual setup_*_processor management commands.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "workflow"

    def ready(self):
        """
        Django startup hook - runs once when the server starts.

        Automatically creates/updates ProcSoftware and Task records from
        processor class definitions, ensuring database stays in sync with code.
        """
        # Import here to avoid AppRegistryNotReady errors

        # Only run sync during normal operation, not during migrations
        import sys

        if "migrate" in sys.argv or "makemigrations" in sys.argv:
            return

        try:
            self._sync_processors_to_database()
        except Exception as e:
            # Log but don't crash - database might not be ready yet
            logger.warning(
                f"Failed to sync processors to database on startup: {e}. "
                f"This is normal during initial setup or migrations."
            )

    def _sync_processors_to_database(self):
        """
        Synchronize all registered processors to database.

        For each processor:
        1. Create/update Task record from task_name
        2. Create/update ProcSoftware record from metadata
        3. Associate Task with ProcSoftware via capable_tasks
        4. Mark processor as active=True

        Mark any ProcSoftware records not in current registry as active=False.
        """
        from processes.models import Task

        from workflow.processors import list_processors

        logger.info("Syncing processor metadata to database...")

        processors = list_processors()
        synced_processor_classes = []
        unsynced_processors = []

        with transaction.atomic():
            for processor_name, processor_class in processors.items():
                try:
                    # Instantiate processor to get metadata
                    processor = processor_class()
                    metadata = processor.get_database_metadata()

                    # Validate metadata
                    if not metadata.get("task_name"):
                        unsynced_processors.append(processor_name)
                        logger.warning(
                            f"Processor '{processor_name}' has no task_name defined. "
                            f"Skipping database sync for this processor."
                        )
                        continue

                    # Create/update Task record
                    task, task_created = Task.objects.get_or_create(
                        name=metadata["task_name"],
                        defaults={"step": 1},  # Default step, can be adjusted manually
                    )

                    if task_created:
                        logger.info(f"  Created Task: {metadata['task_name']}")
                    else:
                        logger.debug(f"  Task exists: {metadata['task_name']}")

                    # Updates ProcSoftware record every startup.
                    software_fields = {
                        "version": metadata["version"],
                        "default_cluster": metadata["default_cluster"],
                        "allowed_clusters": metadata["allowed_clusters"],
                        "active": True,
                    }
                    proc_software, software_created = self._claim_software(metadata, software_fields)

                    action = "Created" if software_created else "Updated"
                    logger.info(
                        f"  {action} ProcSoftware: {proc_software.name} "
                        f"(v{proc_software.version}, {proc_software.processor_class})"
                    )

                    # Associate Task with ProcSoftware via capable_tasks
                    if task not in proc_software.capable_tasks.all():
                        proc_software.capable_tasks.add(task)
                        logger.info(f"  Associated Task '{task.name}' with ProcSoftware '{proc_software.name}'")

                    synced_processor_classes.append(metadata["processor_class"])

                except Exception as e:
                    unsynced_processors.append(processor_name)
                    logger.exception(f"Failed to sync processor '{processor_name}' to database: {e}")

            self._deactivate_orphans(synced_processor_classes, unsynced_processors)

        logger.info(
            f"Processor sync complete: {len(synced_processor_classes)} active processor(s) synchronized to database."
        )

    @staticmethod
    def _claim_software(metadata, software_fields):
        """
        Find this processor's ProcSoftware row, or create one. Returns (row, created).

        Matches on processor_class, then falls back to name across rows where
        processor_class is still NULL
        """
        from processes.models import ProcSoftware

        proc_software = ProcSoftware.objects.filter(processor_class=metadata["processor_class"]).first()

        if proc_software is None:
            proc_software = (
                ProcSoftware.objects.filter(name=metadata["name"], processor_class__isnull=True).order_by("id").first()
            )
            if proc_software is not None:
                logger.info(
                    f"  Adopting pre-existing '{proc_software.name}' "
                    f"(backfilling processor_class='{metadata['processor_class']}')"
                )
                proc_software.processor_class = metadata["processor_class"]

        created = proc_software is None
        if created:
            proc_software = ProcSoftware(
                name=metadata["name"],
                processor_class=metadata["processor_class"],
            )

        for field, value in software_fields.items():
            if field in OPERATOR_OWNED_FIELDS and getattr(proc_software, field, None):
                continue
            setattr(proc_software, field, value)
        proc_software.save()

        return proc_software, created

    @staticmethod
    def _deactivate_orphans(synced_processor_classes, unsynced_processors):
        """
        Mark software whose processor no longer exists in the codebase as inactive.
        """
        from processes.models import ProcSoftware

        if unsynced_processors:
            logger.warning(
                f"  Skipping orphan deactivation: {len(unsynced_processors)} processor(s) did not sync "
                f"({unsynced_processors}). Cannot distinguish a removed processor from a broken one."
            )
            return

        # Compared in Python: exclude(processor_class__in=...) has awkward NULL semantics.
        orphaned = [
            software
            for software in ProcSoftware.objects.filter(active=True)
            if software.processor_class not in synced_processor_classes
        ]

        for software in orphaned:
            if software.pipe_set.exists():
                logger.warning(
                    f"  Keeping '{software.name}' active: no registered processor for "
                    f"'{software.processor_class}', but it still owns pipes."
                )
                continue
            software.active = False
            software.save(update_fields=["active"])
            logger.warning(f"  Marked '{software.name}' as inactive (no longer in codebase)")
