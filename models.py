"""
models.py  —  Core data structures: Thread and GanttSegment.
No GUI imports here — pure logic only.
"""


class Thread:
    """Represents one OS thread throughout its lifecycle."""

    WAITING   = "WAITING"
    READY     = "READY"
    RUNNING   = "RUNNING"
    COMPLETED = "COMPLETED"
    PAUSED    = "PAUSED"
    KILLED    = "KILLED"

    def __init__(self, tid: int, arrival: int, burst: int, priority: int = 1):
        self.tid              = tid
        self.arrival          = arrival
        self.burst            = burst
        self.priority         = priority        # lower = higher priority
        self.remaining        = burst
        self.state            = Thread.WAITING

        # timing fields  (-1 = not set yet)
        self.start_time       = -1
        self.completion_time  = -1
        self.response_time    = -1

        # list of (tick, state) snapshots for the timeline strip
        self.timeline: list[tuple[int, str]] = []

    # ── deep copy ──────────────────────────────────────────────

    def clone(self) -> "Thread":
        t = Thread(self.tid, self.arrival, self.burst, self.priority)
        t.remaining       = self.remaining
        t.state           = self.state
        t.start_time      = self.start_time
        t.completion_time = self.completion_time
        t.response_time   = self.response_time
        t.timeline        = list(self.timeline)
        return t

    # ── derived metrics ────────────────────────────────────────

    @property
    def waiting_time(self) -> int:
        if self.completion_time < 0:
            return -1
        return self.completion_time - self.arrival - self.burst

    @property
    def turnaround_time(self) -> int:
        if self.completion_time < 0:
            return -1
        return self.completion_time - self.arrival

    # ── helpers ────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """True while the thread can still consume CPU time."""
        return self.state not in (Thread.COMPLETED, Thread.KILLED)

    def __repr__(self) -> str:
        return (f"Thread(T{self.tid} arr={self.arrival} burst={self.burst} "
                f"pri={self.priority} rem={self.remaining} {self.state})")


class GanttSegment:
    """One coloured block on the Gantt chart."""

    def __init__(self, tid: int, start: int, end: int, seg_type: str = "run"):
        self.tid      = tid        # 0 = CPU idle
        self.start    = start
        self.end      = end
        self.seg_type = seg_type   # "run" | "idle"

    @property
    def duration(self) -> int:
        return self.end - self.start

    def __repr__(self) -> str:
        label = "IDLE" if self.tid == 0 else f"T{self.tid}"
        return f"GanttSegment({label} [{self.start}–{self.end}])"
