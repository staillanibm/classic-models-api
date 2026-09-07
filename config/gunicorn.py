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
import threading
import time

#: How often each worker refreshes the outbox-backlog gauge. The backlog only
#: matters on the scale of hours or days (it grows while the relay is off),
#: so this trades a little staleness for one cheap indexed query per worker
#: per tick rather than one per scrape.
OUTBOX_GAUGE_POLL_SECONDS = 60


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


def post_worker_init(worker):
    """Worker: start polling the outbox backlog for its unpublished-count gauge.

    Driven by a timer rather than by whichever request happens to land on this
    worker (a Prometheus scrape or a kubelet probe might always land on a
    different one): the whole reason this gauge exists is to be visible without
    anyone having to ask for it.
    """

    def _loop():
        from events.metrics import refresh_outbox_unpublished_gauge

        while True:
            try:
                refresh_outbox_unpublished_gauge()
            except Exception:
                # A blip here must not take the worker down; the next tick retries.
                pass
            time.sleep(OUTBOX_GAUGE_POLL_SECONDS)

    threading.Thread(target=_loop, daemon=True).start()
