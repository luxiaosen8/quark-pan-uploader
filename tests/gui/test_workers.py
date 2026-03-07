from quark_uploader.gui.workers import UploadWorker, WorkerState
from quark_uploader.services.cancellation import UploadCancellationToken


class FakeExecutor:
    def __init__(self, token: UploadCancellationToken | None = None):
        self.token = token
        self.calls = []

    def execute_job(self, job, cancel_token=None):
        self.calls.append(job.local_name)
        if self.token is not None:
            self.token.request_stop()
        return type("Result", (), {"status": "completed", "uploaded_files": 1, "share_url": "", "retry_count": 0})()


def test_worker_state_defaults_to_idle():
    state = WorkerState()
    assert state.running is False
    assert state.stop_requested is False


def test_upload_worker_marks_remaining_jobs_stopped_when_cancel_requested_mid_run():
    token = UploadCancellationToken()
    jobs = [type("Job", (), {"local_name": "A"})(), type("Job", (), {"local_name": "B"})()]
    worker = UploadWorker(plan=type("Plan", (), {"jobs": jobs})(), executor_factory=lambda logger=None: FakeExecutor(token), cancel_token=token)
    task_updates = []
    finished_states = []
    worker.task_status.connect(lambda name, status, share_url, retry_count: task_updates.append((name, status, retry_count)))
    worker.run_finished.connect(lambda status: finished_states.append(status))

    worker.run()

    assert ("A", "completed", 0) in task_updates
    assert ("B", "stopped", 0) in task_updates
    assert finished_states == ["stopped"]



def test_upload_worker_handle_runs_in_background_thread(qtbot):
    import time
    from quark_uploader.gui.workers import UploadWorkerHandle

    class SlowExecutor:
        def execute_job(self, job, cancel_token=None):
            time.sleep(0.2)
            return type("Result", (), {"status": "completed", "uploaded_files": 1, "share_url": "", "retry_count": 0})()

    token = UploadCancellationToken()
    jobs = [type("Job", (), {"local_name": "A"})()]
    worker = UploadWorker(plan=type("Plan", (), {"jobs": jobs})(), executor_factory=lambda logger=None: SlowExecutor(), cancel_token=token)
    finished_states = []
    worker.run_finished.connect(lambda status: finished_states.append(status))
    handle = UploadWorkerHandle(worker)

    handle.start()

    assert handle.is_running() is True
    qtbot.waitUntil(lambda: finished_states == ["completed"], timeout=3000)
    assert handle.is_running() is False
