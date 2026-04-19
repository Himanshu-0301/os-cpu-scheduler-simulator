"""
schedulers.py  —  Scheduling algorithms (offline batch) + StepSimulator.

Offline runners  : run_fcfs, run_rr, run_sjf, run_priority
                   Used by the Analysis tab (graphs) — full-speed, no GUI.

StepSimulator    : Tick-by-tick engine that feeds the live Simulation tab.
                   Exposes pause / resume / kill and a snapshot() method.
"""

from collections import deque
from models import Thread, GanttSegment


# ─────────────────────────────────────────────────────────────
#  SHARED HELPERS
# ─────────────────────────────────────────────────────────────

def _make_threads(cfgs: list[dict]) -> list[Thread]:
    return [Thread(c["id"], c["arrival"], c["burst"], c.get("priority", 1))
            for c in cfgs]

def _seed_arrivals(threads: list[Thread], ready, t: int) -> None:
    """Move every WAITING thread whose arrival == t into ready."""
    for th in threads:
        if th.arrival == t and th.state == Thread.WAITING:
            th.state = Thread.READY
            ready.append(th)

def _seed_up_to(threads: list[Thread], ready, t: int) -> None:
    """Move every WAITING thread whose arrival <= t into ready (for SJF/Priority)."""
    for th in threads:
        if th.arrival <= t and th.state == Thread.WAITING:
            th.state = Thread.READY
            ready.append(th)


# ─────────────────────────────────────────────────────────────
#  OFFLINE SCHEDULERS
# ─────────────────────────────────────────────────────────────

def run_fcfs(cfgs: list[dict]):
    """First Come First Served — non-preemptive, ordered by arrival."""
    threads = _make_threads(cfgs)
    gantt: list[GanttSegment] = []
    t = busy = 0
    q: deque[Thread] = deque()
    _seed_arrivals(threads, q, 0)

    cap = sum(c["burst"] for c in cfgs) + len(cfgs) + 10
    while any(th.state != Thread.COMPLETED for th in threads) and t < cap:
        if not q:
            pend = [th for th in threads if th.state == Thread.WAITING]
            if not pend:
                break
            nxt = min(th.arrival for th in pend)
            gantt.append(GanttSegment(0, t, nxt, "idle"))
            t = nxt
            _seed_arrivals(threads, q, t)
            continue
        th = q.popleft()
        if th.start_time < 0:
            th.start_time = t
            th.response_time = t - th.arrival
        th.state = Thread.RUNNING
        s = t
        while th.remaining > 0:
            t += 1; busy += 1; th.remaining -= 1
            _seed_arrivals(threads, q, t)
        th.state = Thread.COMPLETED
        th.completion_time = t
        gantt.append(GanttSegment(th.tid, s, t))
    return threads, gantt, t, busy


def run_rr(cfgs: list[dict], quantum: int):
    """Round Robin — preemptive, time quantum."""
    threads = _make_threads(cfgs)
    gantt: list[GanttSegment] = []
    t = busy = 0
    q: deque[Thread] = deque()
    _seed_arrivals(threads, q, 0)

    for _ in range(50_000):
        if all(th.state == Thread.COMPLETED for th in threads):
            break
        if not q:
            pend = [th for th in threads if th.state == Thread.WAITING]
            if not pend:
                break
            nxt = min(th.arrival for th in pend)
            gantt.append(GanttSegment(0, t, nxt, "idle"))
            t = nxt
            _seed_arrivals(threads, q, t)
            continue
        th = q.popleft()
        if th.start_time < 0:
            th.start_time = t
            th.response_time = t - th.arrival
        th.state = Thread.RUNNING
        s = t
        for _ in range(min(quantum, th.remaining)):
            t += 1; busy += 1; th.remaining -= 1
            for o in threads:
                if o.arrival == t and o.state == Thread.WAITING:
                    o.state = Thread.READY
                    q.append(o)
        gantt.append(GanttSegment(th.tid, s, t))
        if th.remaining == 0:
            th.state = Thread.COMPLETED
            th.completion_time = t
        else:
            th.state = Thread.READY
            q.append(th)
    return threads, gantt, t, busy


def run_sjf(cfgs: list[dict]):
    """Shortest Job First — non-preemptive, picks shortest burst."""
    threads = _make_threads(cfgs)
    gantt: list[GanttSegment] = []
    t = busy = 0
    q: list[Thread] = []
    for th in threads:
        if th.arrival == 0:
            th.state = Thread.READY
            q.append(th)

    cap = sum(c["burst"] for c in cfgs) + len(cfgs) + 10
    while any(th.state != Thread.COMPLETED for th in threads) and t < cap:
        q = [x for x in q if x.state == Thread.READY]
        if not q:
            pend = [th for th in threads if th.state == Thread.WAITING]
            if not pend:
                break
            nxt = min(th.arrival for th in pend)
            gantt.append(GanttSegment(0, t, nxt, "idle"))
            t = nxt
            _seed_up_to(threads, q, t)
            continue
        th = min(q, key=lambda x: x.burst)
        q.remove(th)
        if th.start_time < 0:
            th.start_time = t
            th.response_time = t - th.arrival
        th.state = Thread.RUNNING
        s = t
        while th.remaining > 0:
            t += 1; busy += 1; th.remaining -= 1
            for o in threads:
                if o.arrival == t and o.state == Thread.WAITING:
                    o.state = Thread.READY
                    q.append(o)
        th.state = Thread.COMPLETED
        th.completion_time = t
        gantt.append(GanttSegment(th.tid, s, t))
    return threads, gantt, t, busy


def run_priority(cfgs: list[dict]):
    """Priority Scheduling — non-preemptive, lower number = higher priority."""
    threads = _make_threads(cfgs)
    gantt: list[GanttSegment] = []
    t = busy = 0
    q: list[Thread] = []
    for th in threads:
        if th.arrival == 0:
            th.state = Thread.READY
            q.append(th)

    cap = sum(c["burst"] for c in cfgs) + len(cfgs) + 10
    while any(th.state != Thread.COMPLETED for th in threads) and t < cap:
        q = [x for x in q if x.state == Thread.READY]
        if not q:
            pend = [th for th in threads if th.state == Thread.WAITING]
            if not pend:
                break
            nxt = min(th.arrival for th in pend)
            gantt.append(GanttSegment(0, t, nxt, "idle"))
            t = nxt
            _seed_up_to(threads, q, t)
            continue
        th = min(q, key=lambda x: x.priority)
        q.remove(th)
        if th.start_time < 0:
            th.start_time = t
            th.response_time = t - th.arrival
        th.state = Thread.RUNNING
        s = t
        while th.remaining > 0:
            t += 1; busy += 1; th.remaining -= 1
            for o in threads:
                if o.arrival == t and o.state == Thread.WAITING:
                    o.state = Thread.READY
                    q.append(o)
        th.state = Thread.COMPLETED
        th.completion_time = t
        gantt.append(GanttSegment(th.tid, s, t))
    return threads, gantt, t, busy


# ─────────────────────────────────────────────────────────────
#  STEP SIMULATOR  (real-time, GUI-facing)
# ─────────────────────────────────────────────────────────────

class StepSimulator:
    """
    Tick-by-tick simulation engine.  Call step() once per GUI tick.
    Supports FCFS, RR, SJF, Priority, plus live pause/resume/kill.
    """

    def __init__(self, cfgs: list[dict], algo: str = "fcfs", quantum: int = 2):
        self.algo             = algo
        self.quantum          = quantum
        self.tick             = 0
        self.busy             = 0
        self.context_switches = 0

        self.gantt: list[GanttSegment] = []
        self.log:   list[tuple]        = []   # (tick, msg, tag)

        self.threads      = _make_threads(cfgs)
        self.ready_queue  = deque()
        self.current:     Thread | None = None
        self.q_slice      = 0
        self._seg_start   = 0
        self._done        = False

        self._paused: set[int] = set()
        self._killed: set[int] = set()

        # seed t=0 arrivals before first step
        self._arrive(0)

    # ── arrival processing ────────────────────────────────────

    def _arrive(self, t: int) -> None:
        for th in self.threads:
            if th.arrival == t and th.state == Thread.WAITING:
                if th.tid in self._killed:
                    th.state = Thread.KILLED
                    continue
                th.state = Thread.READY
                self.ready_queue.append(th)
                th.timeline.append((t, Thread.READY))
                self.log.append(
                    (t, f"T{th.tid} arrived  burst={th.burst}  priority={th.priority}", "arrive"))

    # ── dispatch ──────────────────────────────────────────────

    def _dispatch(self, th: Thread) -> None:
        prev = self.current
        self.current    = th
        self._seg_start = self.tick
        if th.start_time < 0:
            th.start_time    = self.tick
            th.response_time = self.tick - th.arrival
        th.state = Thread.RUNNING
        th.timeline.append((self.tick, Thread.RUNNING))
        if prev is not None and prev.tid != th.tid:
            self.context_switches += 1
        self.log.append(
            (self.tick, f"T{th.tid} → CPU  remaining={th.remaining}", "run"))

    def _complete(self, th: Thread) -> None:
        th.state            = Thread.COMPLETED
        th.completion_time  = self.tick
        th.timeline.append((self.tick, Thread.COMPLETED))
        self.gantt.append(GanttSegment(th.tid, self._seg_start, self.tick))
        self.log.append((self.tick,
            f"T{th.tid} completed  WT={th.waiting_time}  TAT={th.turnaround_time}",
            "complete"))
        self.current = None

    # ── public state ──────────────────────────────────────────

    def is_done(self) -> bool:
        return self._done

    def _ready_list(self) -> list[Thread]:
        return [th for th in self.ready_queue
                if th.state == Thread.READY and th.tid not in self._paused]

    # ── live controls ─────────────────────────────────────────

    def pause_thread(self, tid: int) -> None:
        for th in self.threads:
            if th.tid != tid:
                continue
            if th.state not in (Thread.READY, Thread.RUNNING):
                return
            self._paused.add(tid)
            if th.state == Thread.RUNNING:
                self.gantt.append(GanttSegment(th.tid, self._seg_start, self.tick))
                self.current   = None
                self.q_slice   = 0
            else:
                self.ready_queue = deque(
                    x for x in self.ready_queue if x.tid != tid)
            th.state = Thread.PAUSED
            th.timeline.append((self.tick, Thread.PAUSED))
            self.log.append((self.tick, f"T{tid} paused by user", "pause"))

    def resume_thread(self, tid: int) -> None:
        self._paused.discard(tid)
        for th in self.threads:
            if th.tid == tid and th.state == Thread.PAUSED:
                th.state = Thread.READY
                self.ready_queue.append(th)
                th.timeline.append((self.tick, Thread.READY))
                self.log.append((self.tick, f"T{tid} resumed", "resume"))

    def kill_thread(self, tid: int) -> None:
        self._killed.add(tid)
        for th in self.threads:
            if th.tid == tid and th.state not in (Thread.COMPLETED, Thread.KILLED):
                if th.state == Thread.RUNNING:
                    self.gantt.append(
                        GanttSegment(th.tid, self._seg_start, self.tick))
                    self.current = None
                    self.q_slice = 0
                self.ready_queue = deque(
                    x for x in self.ready_queue if x.tid != tid)
                th.state = Thread.KILLED
                th.timeline.append((self.tick, Thread.KILLED))
                self.log.append((self.tick, f"T{tid} killed by user", "kill"))

    # ── main step ─────────────────────────────────────────────

    def step(self) -> bool:
        """Advance one tick. Returns False when all threads are done/killed."""
        if self._done:
            return False

        self.tick += 1
        self._arrive(self.tick)

        # record idle state for non-running threads
        for th in self.threads:
            if th.state == Thread.WAITING:
                th.timeline.append((self.tick, Thread.WAITING))
            elif th.state == Thread.READY:
                th.timeline.append((self.tick, Thread.READY))
            elif th.state == Thread.PAUSED:
                th.timeline.append((self.tick, Thread.PAUSED))

        # dispatch chosen algorithm
        if self.algo == "rr":
            self._step_rr()
        elif self.algo == "sjf":
            self._step_nonpre(key=lambda x: x.burst)
        elif self.algo == "priority":
            self._step_nonpre(key=lambda x: x.priority)
        else:
            self._step_nonpre(key=lambda x: (x.arrival, x.tid))

        # check completion
        if not any(th.is_active for th in self.threads) and self.current is None:
            self._done = True
            self.log.append((self.tick, "All threads finished", "done"))
            return False
        return True

    # ── algorithm implementations ─────────────────────────────

    def _step_nonpre(self, key) -> None:
        """Generic non-preemptive step (FCFS / SJF / Priority)."""
        if self.current is None:
            q = sorted(self._ready_list(), key=key)
            if q:
                chosen = q[0]
                self.ready_queue.remove(chosen)
                self._dispatch(chosen)
            else:
                return   # CPU idle this tick
        th = self.current
        th.remaining -= 1
        self.busy    += 1
        if th.remaining == 0:
            self._complete(th)

    def _step_rr(self) -> None:
        """Round Robin step."""
        if self.current is not None:
            th = self.current
            th.remaining -= 1
            self.busy    += 1
            self.q_slice += 1
            if th.remaining == 0:
                self._complete(th)
                self.q_slice = 0
            elif self.q_slice >= self.quantum:
                self.gantt.append(
                    GanttSegment(th.tid, self._seg_start, self.tick))
                self.log.append((self.tick,
                    f"T{th.tid} preempted  quantum={self.quantum}", "preempt"))
                th.state = Thread.READY
                self.ready_queue.append(th)
                th.timeline.append((self.tick, Thread.READY))
                self.current = None
                self.q_slice = 0

        q = self._ready_list()
        if self.current is None and q:
            chosen = q[0]
            self.ready_queue.remove(chosen)
            self._dispatch(chosen)

    # ── snapshot ──────────────────────────────────────────────

    def snapshot(self) -> dict:
        return {
            "tick":             self.tick,
            "threads":          [th.clone() for th in self.threads],
            "queue":            list(self.ready_queue),
            "current":          self.current.clone() if self.current else None,
            "gantt":            list(self.gantt),
            "busy":             self.busy,
            "context_switches": self.context_switches,
            "log":              list(self.log),
        }
