from quark_uploader.gui.workers import WorkerState


def test_worker_state_defaults_to_idle():
    state = WorkerState()
    assert state.running is False
    assert state.stop_requested is False
