"""
server.py  —  Flask API layer for the OS Thread Simulator.
Wraps the existing scheduling engine (models.py + schedulers.py) with REST endpoints.
"""

from flask import Flask, request, jsonify, send_from_directory
import os, sys

# Ensure the directory containing server.py is always on the path,
# whether the script is run directly or from another working directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from schedulers import run_fcfs, run_rr, run_sjf, run_priority, StepSimulator
from models import Thread, GanttSegment

app = Flask(__name__, static_folder="static")

# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────

def _threads_to_json(threads):
    return [
        {
            "id":              t.tid,
            "arrival":         t.arrival,
            "burst":           t.burst,
            "priority":        t.priority,
            "state":           t.state,
            "waiting_time":    max(t.waiting_time,   0) if t.completion_time >= 0 else None,
            "turnaround_time": max(t.turnaround_time,0) if t.completion_time >= 0 else None,
            "response_time":   t.response_time if t.response_time >= 0 else None,
            "completion_time": t.completion_time if t.completion_time >= 0 else None,
            "start_time":      t.start_time if t.start_time >= 0 else None,
        }
        for t in threads
    ]

def _gantt_to_json(gantt):
    return [
        {"tid": g.tid, "start": g.start, "end": g.end,
         "duration": g.duration, "type": g.seg_type}
        for g in gantt
    ]

def _metrics(threads, gantt, total_time, busy):
    completed = [t for t in threads if t.completion_time >= 0]
    n = len(completed)
    avg_wt  = round(sum(max(t.waiting_time,   0) for t in completed) / n, 2) if n else 0
    avg_tat = round(sum(max(t.turnaround_time, 0) for t in completed) / n, 2) if n else 0
    avg_rt  = round(sum(t.response_time for t in completed if t.response_time >= 0) / n, 2) if n else 0
    cpu_util = round((busy / total_time * 100), 1) if total_time > 0 else 0
    # count context switches in gantt
    ctx = 0
    prev_tid = None
    for seg in gantt:
        if seg.tid != 0 and seg.tid != prev_tid and prev_tid is not None:
            ctx += 1
        prev_tid = seg.tid
    return {
        "avg_waiting_time":    avg_wt,
        "avg_turnaround_time": avg_tat,
        "avg_response_time":   avg_rt,
        "cpu_utilization":     cpu_util,
        "throughput":          round(n / total_time, 3) if total_time > 0 else 0,
        "context_switches":    ctx,
        "total_time":          total_time,
        "threads_completed":   n,
    }

def _build_logs(threads, gantt, total_time):
    """Build structured tick-by-tick log from gantt segments."""
    logs = []
    # collect arrivals per tick
    arrivals_map = {}
    completions_map = {}
    for t in threads:
        arrivals_map.setdefault(t.arrival, []).append(f"T{t.tid}")
        if t.completion_time >= 0:
            completions_map.setdefault(t.completion_time, []).append(f"T{t.tid}")

    # build timeline from gantt
    for seg in gantt:
        if seg.tid == 0:
            for tick in range(seg.start, seg.end):
                logs.append({
                    "time": tick,
                    "cpu": {"running": "IDLE", "remaining": 0},
                    "arrivals":  arrivals_map.get(tick, []),
                    "completed": completions_map.get(tick, []),
                })
        else:
            th = next((t for t in threads if t.tid == seg.tid), None)
            for i, tick in enumerate(range(seg.start, seg.end)):
                remaining = (th.burst - (tick - th.start_time)) if th else 0
                logs.append({
                    "time": tick,
                    "cpu": {"running": f"T{seg.tid}", "remaining": max(remaining, 0)},
                    "arrivals":  arrivals_map.get(tick, []),
                    "completed": completions_map.get(tick, []),
                })
    logs.sort(key=lambda x: x["time"])
    return logs


def _validate_cfgs(data):
    threads = data.get("threads", [])
    if not threads:
        return None, "No threads provided"
    cfgs = []
    for i, t in enumerate(threads):
        try:
            cfgs.append({
                "id":       int(t.get("id", i + 1)),
                "arrival":  int(t.get("arrival", 0)),
                "burst":    max(1, int(t.get("burst", 1))),
                "priority": int(t.get("priority", 1)),
            })
        except (ValueError, TypeError) as e:
            return None, f"Invalid thread data: {e}"
    return cfgs, None


# ─────────────────────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/simulate", methods=["POST"])
def simulate():
    data = request.get_json(force=True)
    cfgs, err = _validate_cfgs(data)
    if err:
        return jsonify({"error": err}), 400

    algo    = data.get("algorithm", "fcfs").lower()
    quantum = max(1, int(data.get("quantum", 2)))

    runners = {
        "fcfs":     lambda: run_fcfs(cfgs),
        "rr":       lambda: run_rr(cfgs, quantum),
        "sjf":      lambda: run_sjf(cfgs),
        "priority": lambda: run_priority(cfgs),
    }
    if algo not in runners:
        return jsonify({"error": f"Unknown algorithm: {algo}"}), 400

    threads, gantt, total_time, busy = runners[algo]()

    return jsonify({
        "algorithm":  algo.upper() if algo != "rr" else "Round Robin",
        "threads":    _threads_to_json(threads),
        "gantt":      _gantt_to_json(gantt),
        "metrics":    _metrics(threads, gantt, total_time, busy),
        "logs":       _build_logs(threads, gantt, total_time),
        "quantum":    quantum if algo == "rr" else None,
    })


@app.route("/compare", methods=["POST"])
def compare():
    data = request.get_json(force=True)
    cfgs, err = _validate_cfgs(data)
    if err:
        return jsonify({"error": err}), 400

    quantum = max(1, int(data.get("quantum", 2)))

    results = {}
    for algo, runner in [
        ("FCFS",     lambda: run_fcfs(cfgs)),
        ("RR",       lambda: run_rr(cfgs, quantum)),
        ("SJF",      lambda: run_sjf(cfgs)),
        ("Priority", lambda: run_priority(cfgs)),
    ]:
        threads, gantt, total_time, busy = runner()
        results[algo] = {
            "threads": _threads_to_json(threads),
            "gantt":   _gantt_to_json(gantt),
            "metrics": _metrics(threads, gantt, total_time, busy),
        }
    return jsonify(results)


@app.route("/insights", methods=["POST"])
def insights():
    data = request.get_json(force=True)
    cfgs, err = _validate_cfgs(data)
    if err:
        return jsonify({"error": err}), 400

    quantum = max(1, int(data.get("quantum", 2)))

    algo_data = {}
    for algo, runner in [
        ("FCFS",     lambda: run_fcfs(cfgs)),
        ("RR",       lambda: run_rr(cfgs, quantum)),
        ("SJF",      lambda: run_sjf(cfgs)),
        ("Priority", lambda: run_priority(cfgs)),
    ]:
        threads, gantt, total_time, busy = runner()
        algo_data[algo] = _metrics(threads, gantt, total_time, busy)

    # rank by avg waiting time (lower = better)
    ranked = sorted(algo_data.items(), key=lambda x: x[1]["avg_waiting_time"])
    best   = ranked[0][0]

    # generate textual insights
    best_m = algo_data[best]
    insights_text = []

    insights_text.append(f"**{best}** delivers the lowest average waiting time of {best_m['avg_waiting_time']} ticks.")

    if best == "SJF":
        insights_text.append("SJF minimizes average waiting time by always executing the shortest available job first — optimal for batch workloads where burst times are known in advance.")
    elif best == "FCFS":
        insights_text.append("FCFS performs well here because arrival times are evenly spread, reducing the convoy effect. Ideal for uniform workloads.")
    elif best == "RR":
        insights_text.append(f"Round Robin (quantum={quantum}) balances CPU time fairly across threads, making it optimal for interactive/time-sharing systems.")
    elif best == "Priority":
        insights_text.append("Priority Scheduling is effective when thread importance varies significantly — critical threads complete faster at the cost of lower-priority ones.")

    # CPU utilization note
    best_cpu = max(algo_data.items(), key=lambda x: x[1]["cpu_utilization"])
    if best_cpu[0] != best:
        insights_text.append(f"**{best_cpu[0]}** achieves the highest CPU utilization ({best_cpu[1]['cpu_utilization']}%), minimizing idle time.")

    # context switch note
    ctx_data = {k: v["context_switches"] for k, v in algo_data.items()}
    lowest_ctx = min(ctx_data, key=ctx_data.get)
    insights_text.append(f"**{lowest_ctx}** has the fewest context switches ({ctx_data[lowest_ctx]}), reducing OS overhead.")

    # recommendation
    n_threads = len(cfgs)
    bursts = [c["burst"] for c in cfgs]
    variance = max(bursts) - min(bursts)
    if variance > 5:
        rec = "SJF or Priority — burst time variance is high, so shortest-first or priority ordering significantly reduces average wait."
    elif n_threads <= 3:
        rec = "FCFS — low thread count means convoy effect is minimal and simplicity wins."
    else:
        rec = "Round Robin — with multiple threads of similar burst length, fair time-sharing prevents starvation."

    return jsonify({
        "best_algorithm":  best,
        "ranking":         [{"rank": i+1, "algorithm": a, "avg_waiting_time": m["avg_waiting_time"],
                             "avg_turnaround_time": m["avg_turnaround_time"],
                             "cpu_utilization": m["cpu_utilization"]}
                            for i, (a, m) in enumerate(ranked)],
        "analysis":        algo_data,
        "insights":        insights_text,
        "recommendation":  rec,
    })


if __name__ == "__main__":
    print("\n  OS Thread Simulator running at http://localhost:5000\n")
    app.run(debug=True, port=5000)
