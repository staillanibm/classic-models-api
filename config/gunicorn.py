"""Gunicorn config — aggregating Prometheus metrics across workers.

Without this, every gunicorn worker keeps its own in-memory registry and a
/metrics scrape lands on whichever worker happens to answer: counters appear to
oscillate and undercount by roughly the worker count.

prometheus_client solves this with a shared directory (PROMETHEUS_MULTIPROC_DIR)
where each process mmaps its samples; the export view aggregates them at read
time. Two obligations follow:
  * start the master from an empty directory, otherwise files left by the
    previous run's workers are counted again;
  * mark each worker dead when it exits, so its gauges stop being aggregated.
"""

import os
import shutil


def _multiproc_dir():
    return os.environ.get("PROMETHEUS_MULTIPROC_DIR")


def on_starting(server):
    """Master: start from a clean metrics directory.

    Creating the directory itself lives in the Django settings, which every
    entrypoint loads (including the migrate Job, which never goes through
    gunicorn). Here we only purge leftovers from the previous run.
    """
    path = _multiproc_dir()
    if not path:
        return
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)


def child_exit(server, worker):
    """Worker gone: its samples must no longer be aggregated."""
    if not _multiproc_dir():
        return
    from prometheus_client import multiprocess

    multiprocess.mark_process_dead(worker.pid)
