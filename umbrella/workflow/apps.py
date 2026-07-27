"""
Workflow App Configuration

Handles automatic synchronization of processor metadata to database on server startup.
"""

import logging

from django.apps import AppConfig
from django.db import transaction

logger = logging.getLogger(__name__)


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
        from processes.models import ProcSoftware, Task

        from workflow.processors import list_processors

        logger.info("Syncing processor metadata to database...")

        processors = list_processors()
        synced_processor_names = []

        with transaction.atomic():
            for processor_name, processor_class in processors.items():
                try:
                    # Instantiate processor to get metadata
                    processor = processor_class()
                    metadata = processor.get_database_metadata()

                    # Validate metadata
                    if not metadata.get("task_name"):
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

                    # Create/update ProcSoftware record (always overwrite with class values)
                    proc_software, software_created = ProcSoftware.objects.update_or_create(
                        name=metadata["name"],
                        defaults={
                            "version": metadata["version"],
                            "processor_class": metadata["processor_class"],
                            "default_cluster": metadata["default_cluster"],
                            "allowed_clusters": metadata["allowed_clusters"],
                            "script_directory": metadata["script_directory"],
                            "active": True,
                        },
                    )

                    if software_created:
                        logger.info(
                            f"  Created ProcSoftware: {metadata['name']} "
                            f"(v{metadata['version']}, {metadata['processor_class']})"
                        )
                    else:
                        logger.info(
                            f"  Updated ProcSoftware: {metadata['name']} "
                            f"(v{metadata['version']}, {metadata['processor_class']})"
                        )

                    # Associate Task with ProcSoftware via capable_tasks
                    if task not in proc_software.capable_tasks.all():
                        proc_software.capable_tasks.add(task)
                        logger.info(f"  Associated Task '{task.name}' with ProcSoftware '{proc_software.name}'")

                    synced_processor_names.append(metadata["name"])

                except Exception as e:
                    logger.error(f"Failed to sync processor '{processor_name}' to database: {e}", exc_info=True)

            # Mark processors not in current registry as inactive
            orphaned = ProcSoftware.objects.exclude(name__in=synced_processor_names)
            orphaned_count = orphaned.filter(active=True).count()
            if orphaned_count > 0:
                orphaned.update(active=False)
                orphaned_names = list(orphaned.values_list("name", flat=True))
                logger.warning(
                    f"  Marked {orphaned_count} processor(s) as inactive (no longer in codebase): {orphaned_names}"
                )

        logger.info(
            f"Processor sync complete: {len(synced_processor_names)} active processor(s) synchronized to database."
        )
