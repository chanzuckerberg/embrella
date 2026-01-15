"""
Management command to submit a filesystem survey SLURM job.

This command creates a FilesystemSurvey record and submits a SLURM job
that discovers all files on a cluster path, outputting to a Parquet file.

Zarr Caching:
    Zarr directories contain thousands of files and `du -sb` is very slow (~1000x).
    When re-running surveys, we extract zarr entries from the previous survey's
    Parquet file and upload as a cache. The SLURM script skips `du` for zarrs
    whose mtime hasn't changed.

Usage:
    python manage.py submit_filesystem_survey --cluster bruno --path /hpc/projects/krios1.processing/
    python manage.py submit_filesystem_survey --cluster czii --path /hpc/projects/group.czii/ --dry-run
    python manage.py submit_filesystem_survey --cluster czii --path /hpc/projects/group.czii/ --no-cache
"""
import json
import os
import re
import tempfile

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from jinja2 import Environment, FileSystemLoader
from umbrella_logger import logger

from common import clusterio
from processes.models import FilesystemSurvey


class Command(BaseCommand):
    help = 'Submit a filesystem survey SLURM job to discover all files on a cluster path'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cluster',
            type=str,
            required=True,
            choices=['czii', 'bruno'],
            help='Cluster to run the survey on',
        )
        parser.add_argument(
            '--path',
            type=str,
            required=True,
            help='Base path to survey (e.g., /hpc/projects/krios1.processing/)',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            help='Output directory for survey results (default: /hpc/projects/<cluster>/surveys/)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show the rendered script without submitting',
        )
        parser.add_argument(
            '--partition',
            type=str,
            default='cpu',
            help='SLURM partition to use (default: cpu)',
        )
        parser.add_argument(
            '--time-limit',
            type=str,
            default='48:00:00',
            help='SLURM time limit (default: 48:00:00)',
        )
        parser.add_argument(
            '--cpus',
            type=int,
            default=4,
            help='Number of CPUs (default: 4)',
        )
        parser.add_argument(
            '--memory',
            type=str,
            default='32G',
            help='Memory allocation (default: 32G)',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username to attribute this survey to (default: first superuser)',
        )
        parser.add_argument(
            '--python-env',
            type=str,
            default='/hpc/projects/group.czii/krios1.processing/software/broom',
            help='Conda environment with pyarrow installed',
        )
        parser.add_argument(
            '--no-cache',
            action='store_true',
            help='Disable zarr cache from previous surveys (recompute all zarr sizes)',
        )

    def handle(self, *args, **options):
        cluster = options['cluster']
        base_path = options['path']
        dry_run = options['dry_run']
        use_cache = not options['no_cache']

        # Validate base path
        if not base_path.startswith('/'):
            self.stderr.write(self.style.ERROR('Base path must be an absolute path'))
            return

        # Get output directory
        if options['output_dir']:
            output_dir = options['output_dir']
        else:
            # Default output directory
            output_dir = '/hpc/projects/group.czii/michael.souza/surveys'

        # Get user
        if options['user']:
            try:
                user = User.objects.get(username=options['user'])
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"User '{options['user']}' not found"))
                return
        else:
            # Use first superuser
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                self.stderr.write(self.style.WARNING('No superuser found, survey will have no owner'))
                user = None

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))

        # Check for zarr cache from previous survey
        zarr_cache_path = None
        if use_cache:
            zarr_cache_path = self._prepare_zarr_cache(cluster, base_path, output_dir, dry_run)

        # Create FilesystemSurvey record (even in dry run, to get an ID for the script)
        if not dry_run:
            survey = FilesystemSurvey.objects.create(
                cluster=cluster,
                base_path=base_path,
                status='pending',
                submitted_by=user,
            )
            survey_id = survey.id
            self.stdout.write(self.style.SUCCESS(f'Created FilesystemSurvey record: {survey_id}'))
        else:
            # Use a placeholder ID for dry run
            survey_id = 'DRY_RUN'

        # Calculate parquet output path
        parquet_path = f'{output_dir}/survey_{survey_id}.parquet'

        # Render the SLURM script
        template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'templates')
        template_dir = os.path.abspath(template_dir)

        if not os.path.exists(os.path.join(template_dir, 'filesystem_survey.sh.j2')):
            self.stderr.write(self.style.ERROR(f'Template not found at {template_dir}/filesystem_survey.sh.j2'))
            if not dry_run:
                survey.status = 'failed'
                survey.error_message = 'Template not found'
                survey.save()
            return

        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('filesystem_survey.sh.j2')

        rendered_script = template.render(
            survey_id=survey_id,
            base_path=base_path,
            output_dir=output_dir,
            partition=options['partition'],
            time_limit=options['time_limit'],
            cpus=options['cpus'],
            memory=options['memory'],
            python_env=options['python_env'],
            mail_user=user.email if user and user.email else None,
            zarr_cache_path=zarr_cache_path,
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('\n=== Rendered SLURM Script ===\n'))
            self.stdout.write(rendered_script)
            self.stdout.write(self.style.WARNING('\n=== End Script ===\n'))
            self.stdout.write(f'Cluster: {cluster}')
            self.stdout.write(f'Base path: {base_path}')
            self.stdout.write(f'Output directory: {output_dir}')
            self.stdout.write(f'Parquet output: {parquet_path}')
            return

        # Submit the job
        try:
            from workflow.agent import RemoteJobSubmitter

            # Get auth from environment
            auth = {
                'username': os.getenv('SLURM_USER'),
                'key_filename': os.getenv('SLURM_KEYFILE'),
            }

            if not auth['username'] or not auth['key_filename']:
                raise ValueError(
                    'SLURM_USER and SLURM_KEYFILE environment variables must be set. '
                    'See docs/contributing/environments.md for details.',
                )

            # Use surveys directory for scripts
            remote_script_dir = output_dir

            submitter = RemoteJobSubmitter(
                cluster_id=cluster,
                auth=auth,
                remote_script_dir=remote_script_dir,
            )

            self.stdout.write(f'Connecting to {cluster}...')
            submitter.connect()

            try:
                job_name = f'fs_survey_{survey_id}'
                self.stdout.write(f'Submitting job {job_name}...')

                output, error = submitter.run_script(
                    template_path=None,
                    job_name=job_name,
                    script_content=rendered_script,
                )

                if error:
                    logger.warning(f'SLURM stderr: {error}')

                # Parse job ID
                job_id = self._parse_job_id(output)

                if job_id:
                    survey.job_id = job_id
                    survey.status = 'submitted'
                    survey.submitted_at = timezone.now()
                    survey.results_parquet_path = parquet_path
                    survey.save()

                    self.stdout.write(self.style.SUCCESS('Job submitted successfully!'))
                    self.stdout.write(f'  Job ID: {job_id}')
                    self.stdout.write(f'  Survey ID: {survey_id}')
                    self.stdout.write(f'  Parquet output: {parquet_path}')

                    # Start the survey status syncer
                    try:
                        from processes.tasks import start_survey_status_syncer
                        start_survey_status_syncer(survey_id=survey_id, cluster_id=cluster)
                        self.stdout.write(self.style.SUCCESS('Started survey status syncer'))
                    except ImportError:
                        self.stdout.write(self.style.WARNING(
                            'Survey status syncer not available. '
                            'Monitor job manually with: squeue -j {job_id}',
                        ))

                else:
                    survey.status = 'failed'
                    survey.error_message = f'Could not parse job ID from output: {output}'
                    survey.save()
                    self.stderr.write(self.style.ERROR('Failed to parse job ID'))
                    self.stderr.write(f'Output: {output}')
                    self.stderr.write(f'Error: {error}')

            finally:
                submitter.close()

        except Exception as e:
            logger.error(f'Error submitting survey job: {e}', exc_info=True)
            if not dry_run:
                survey.status = 'failed'
                survey.error_message = str(e)
                survey.save()
            self.stderr.write(self.style.ERROR(f'Error: {e}'))

    def _parse_job_id(self, output: str) -> str | None:
        """Parse job ID from SLURM sbatch output."""
        # Look for "Submitted batch job 12345" pattern
        match = re.search(r'Submitted batch job (\d+)', output)
        if match:
            return match.group(1)

        # Also try heterogeneous job pattern "Submitted batch job 12345+0"
        match = re.search(r'Submitted batch job (\d+\+\d+)', output)
        if match:
            return match.group(1)

        return None

    def _prepare_zarr_cache(self, cluster: str, base_path: str, output_dir: str, dry_run: bool) -> str | None:
        """
        Extract zarr entries from previous survey and upload as cache file.

        Returns the remote path to the cache file, or None if no cache available.
        """
        # Find the most recent completed survey for this cluster/base_path
        previous_survey = (
            FilesystemSurvey.objects.filter(
                cluster=cluster,
                base_path=base_path,
                status='completed',
                results_parquet_path__isnull=False,
            )
            .order_by('-completed_at')
            .first()
        )

        if not previous_survey:
            self.stdout.write('No previous completed survey found for zarr cache')
            return None

        self.stdout.write(
            f'Found previous survey {previous_survey.id} '
            f'(completed {previous_survey.completed_at})',
        )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'  Would extract zarr cache from: {previous_survey.results_parquet_path}',
            ))
            return f'{output_dir}/zarr_cache_from_{previous_survey.id}.json'

        try:
            import duckdb

            # Get auth from environment
            auth = {
                'username': os.getenv('SLURM_USER'),
                'key_filename': os.getenv('SLURM_KEYFILE'),
            }

            if not auth['username'] or not auth['key_filename']:
                self.stdout.write(self.style.WARNING(
                    'SLURM credentials not set, skipping zarr cache',
                ))
                return None

            ssh = clusterio.get_cluster_ssh_connection(cluster_id=cluster, auth=auth)

            try:
                sftp = ssh.open_sftp()

                # Download previous Parquet to temp file
                with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
                    tmp_parquet = tmp.name

                self.stdout.write('  Downloading previous survey Parquet...')
                sftp.get(previous_survey.results_parquet_path, tmp_parquet)

                # Extract zarr entries using DuckDB
                self.stdout.write('  Extracting zarr entries...')
                con = duckdb.connect()
                zarr_entries = con.execute(f"""
                    SELECT path, size, mtime, uid, mode
                    FROM read_parquet('{tmp_parquet}')
                    WHERE type = 'zarr'
                """).fetchall()
                con.close()

                # Clean up temp parquet
                os.unlink(tmp_parquet)

                if not zarr_entries:
                    self.stdout.write('  No zarr entries found in previous survey')
                    sftp.close()
                    return None

                self.stdout.write(f'  Found {len(zarr_entries)} zarr entries to cache')

                # Create cache JSON: {path: {size, mtime, uid, mode}, ...}
                cache_data = {}
                for path, size, mtime, uid, mode in zarr_entries:
                    cache_data[path] = {
                        'size': size,
                        'mtime': mtime,
                        'uid': uid,
                        'mode': mode,
                    }

                # Write cache to temp file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                    json.dump(cache_data, tmp)
                    tmp_cache = tmp.name

                # Upload cache to cluster
                remote_cache_path = f'{output_dir}/zarr_cache_from_{previous_survey.id}.json'

                # Ensure output directory exists
                try:
                    sftp.stat(output_dir)
                except FileNotFoundError:
                    sftp.mkdir(output_dir)

                self.stdout.write(f'  Uploading zarr cache to {remote_cache_path}...')
                sftp.put(tmp_cache, remote_cache_path)
                sftp.close()

                # Clean up temp cache file
                os.unlink(tmp_cache)

                self.stdout.write(self.style.SUCCESS(
                    f'  Zarr cache ready: {len(zarr_entries)} entries',
                ))
                return remote_cache_path

            finally:
                ssh.close()

        except Exception as e:
            logger.warning(f'Error preparing zarr cache: {e}')
            self.stdout.write(self.style.WARNING(
                f'  Could not prepare zarr cache: {e}',
            ))
            return None
