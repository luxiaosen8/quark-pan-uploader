from dataclasses import dataclass


@dataclass
class WorkerState:
    running: bool = False
    stop_requested: bool = False
