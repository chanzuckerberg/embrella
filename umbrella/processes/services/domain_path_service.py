"""
Service to extract paths from domain models for entity-directory linking.

This service replaces the ProcessingDataTracker-based origin detection
by querying domain models directly to identify app-generated directories.
"""
from django.contrib.contenttypes.models import ContentType

from processes.models import (
    Alignment,
    Annotation,
    Ctf,
    Frames,
    ParticleGallery,
    RawTiltSeries,
    TiltAngles,
    Tomograms,
)


class DomainPathService:
    """Extracts paths from domain models for linking with DirectorySummary."""

    @staticmethod
    def get_directory_from_path(path_str: str) -> str | None:
        """Extract parent directory from a file path."""
        if not path_str:
            return None
        # Remove trailing slash if present, then get parent
        path_str = path_str.rstrip('/')
        parts = path_str.split('/')
        if len(parts) > 1:
            return '/'.join(parts[:-1])
        return None

    @classmethod
    def get_all_entity_paths(cls) -> dict:
        """
        Returns a dictionary mapping directory paths to entity information.

        Returns:
            dict: {
                '/path/to/dir': {
                    'content_type_id': int,
                    'object_id': int,
                    'model_name': str,
                    'full_path': str,
                },
                ...
            }
        """
        path_to_entity = {}

        # Process Frames (uses frame_path FK)
        frames_ct = ContentType.objects.get_for_model(Frames)
        for frame in Frames.objects.select_related('frame_path').exclude(frame_path__isnull=True):
            path_str = str(frame.frame_path) if frame.frame_path else None
            if path_str:
                dir_path = cls.get_directory_from_path(path_str)
                if dir_path:
                    path_to_entity[dir_path] = {
                        'content_type_id': frames_ct.id,
                        'object_id': frame.id,
                        'model_name': 'Frames',
                        'full_path': path_str,
                    }

        # Process models that use pipe_data.path pattern
        pipe_data_models = [
            (RawTiltSeries, 'RawTiltSeries'),
            (TiltAngles, 'TiltAngles'),
            (Ctf, 'Ctf'),
            (Alignment, 'Alignment'),
            (Tomograms, 'Tomograms'),
            (Annotation, 'Annotation'),
            (ParticleGallery, 'ParticleGallery'),
        ]

        for model_class, model_name in pipe_data_models:
            content_type = ContentType.objects.get_for_model(model_class)
            queryset = model_class.objects.select_related('pipe_data', 'pipe_data__path').exclude(
                pipe_data__isnull=True,
            )

            for obj in queryset:
                if obj.pipe_data and obj.pipe_data.path:
                    path_str = str(obj.pipe_data.path)
                    if path_str:
                        dir_path = cls.get_directory_from_path(path_str)
                        if dir_path:
                            path_to_entity[dir_path] = {
                                'content_type_id': content_type.id,
                                'object_id': obj.id,
                                'model_name': model_name,
                                'full_path': path_str,
                            }

        return path_to_entity

    @classmethod
    def get_entity_directories(cls) -> set:
        """
        Returns a set of all directory paths that contain app-generated data.

        This is a simpler version of get_all_entity_paths() for use when
        only origin detection is needed without entity linking.
        """
        return set(cls.get_all_entity_paths().keys())
