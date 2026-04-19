# OS Thread Simulator — Hybrid Web Edition

A real-time CPU scheduling simulator with a Flask backend and modern web dashboard.

## Project Structure

```
os_simulator/
├── server.py         ← Flask API (endpoints: /simulate, /compare, /insights)
├── schedulers.py     ← Scheduling engine (FCFS, RR, SJF, Priority) — unchanged
├── models.py         ← Thread & GanttSegment data classes — unchanged
├── requirements.txt
└── static/
    └── index.html    ← Complete web dashboard (HTML + CSS + JS)
```

## Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the server
```bash
python server.py
```

### 3. Open the dashboard
Visit: **http://localhost:5000**

---

## API Endpoints

### `POST /simulate`
Run a single algorithm and get full results.

**Request:**
```json
{
  "threads": [
    {"id": 1, "arrival": 0, "burst": 6, "priority": 2},
    {"id": 2, "arrival": 2, "burst": 4, "priority": 1}
  ],
  "algorithm": "fcfs",   // fcfs | rr | sjf | priority
  "quantum": 2           // only used for rr
}
```

**Response:**
```json
{
  "algorithm": "FCFS",
  "threads": [...],
  "gantt": [{"tid": 1, "start": 0, "end": 6, "duration": 6, "type": "run"}],
  "metrics": {
    "avg_waiting_time": 2.5,
    "avg_turnaround_time": 6.0,
    "avg_response_time": 1.0,
    "cpu_utilization": 95.2,
    "throughput": 0.18,
    "context_switches": 3,
    "total_time": 11,
    "threads_completed": 4
  },
  "logs": [{"time": 0, "cpu": {"running": "T1", "remaining": 6}, "arrivals": ["T1"], "completed": []}]
}
```

### `POST /compare`
Runs all 4 algorithms and returns side-by-side metrics.

**Request:** Same as `/simulate` (algorithm field is ignored).

**Response:**
```json
{
  "FCFS":     {"threads": [...], "gantt": [...], "metrics": {...}},
  "RR":       {"threads": [...], "gantt": [...], "metrics": {...}},
  "SJF":      {"threads": [...], "gantt": [...], "metrics": {...}},
  "Priority": {"threads": [...], "gantt": [...], "metrics": {...}}
}
```

### `POST /insights`
Generates intelligent analysis and recommendations.

**Request:** Same as `/simulate`.

**Response:**
```json
{
  "best_algorithm": "SJF",
  "ranking": [
    {"rank": 1, "algorithm": "SJF", "avg_waiting_time": 1.5, ...}
  ],
  "analysis": {"FCFS": {...metrics}, ...},
  "insights": ["**SJF** delivers the lowest average waiting time of 1.5 ticks.", ...],
  "recommendation": "SJF or Priority — burst time variance is high..."
}
```

---

## Features

- **Simulate Tab** — Run any single algorithm, see Gantt chart, thread results table, and event log
- **Analysis Tab** — Compare all 4 algorithms with Chart.js bar charts and execution timelines  
- **Insights Tab** — Algorithmic analysis, ranking, key findings, and workload-specific recommendations
- **Presets** — Default, Stress, and Priority Demo thread configurations
- **Dark theme** — Professional OS dashboard aesthetic
