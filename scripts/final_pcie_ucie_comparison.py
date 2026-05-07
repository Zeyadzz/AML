#!/usr/bin/env python3

from pathlib import Path
import re
import statistics

# ============================================================
# Final PCIe vs UCIe Comparison Script
#
# Compares:
# 1. Absolute Link / Path Latency
# 2. SystemC timestamp-based execution time
# 3. Protocol overhead
#
# Expected logs:
# - outputs/pcie_workload_64B/systemc_pcie.log
# - outputs/ucie_workload_64B/systemc_ucie.log
# ============================================================

PCIE_LOG = Path("outputs/pcie_workload_64B/systemc_pcie.log")
UCIE_LOG = Path("outputs/ucie_workload_64B/systemc_ucie.log")

OUT_DIR = Path("results")
OUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_OUT = OUT_DIR / "final_pcie_vs_ucie_comparison_report.txt"

# ============================================================
# Regex patterns
# ============================================================

timestamp_re = re.compile(r"^\s*(\d+)\s+ps")

pcie_tlp_re = re.compile(
    r"PCIe\s+TLP\s+"
    r"id=(?P<id>\d+)\s+"
    r"seq=(?P<seq>\d+)\s+"
    r"payload=(?P<payload>\d+)\s+"
    r"tlp_bytes=(?P<tlp_bytes>\d+)\s+"
    r"rc=(?P<rc>[\d.]+)ns\s+"
    r"link=(?P<link>[\d.]+)ns\s+"
    r"endpoint=(?P<endpoint>[\d.]+)ns\s+"
    r"replay=(?P<replay>[\d.]+)ns\s+"
    r"total=(?P<total>[\d.]+)ns"
)

ucie_flit_re = re.compile(
    r"UCIe\s+Flit\s+"
    r"id=(?P<id>\d+)\s+"
    r"payload=(?P<payload>\d+)\s+"
    r"flit_bytes=(?P<flit_bytes>\d+)\s+"
    r"packer=(?P<packer>[\d.]+)ns\s+"
    r"d2d=(?P<d2d>[\d.]+)ns\s+"
    r"phy=(?P<phy>[\d.]+)ns\s+"
    r"retry=(?P<retry>[\d.]+)ns\s+"
    r"total=(?P<total>[\d.]+)ns"
)

# ============================================================
# Helpers
# ============================================================

def require_file(path: Path, label: str) -> str:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {label} log: {path}\n"
            f"Generate it first, then rerun this script."
        )

    text = path.read_text(errors="ignore")

    if not text.strip():
        raise RuntimeError(f"{label} log exists but is empty: {path}")

    return text


def extract_timestamps_ps(text: str):
    timestamps = []

    for line in text.splitlines():
        m = timestamp_re.search(line)
        if m:
            timestamps.append(int(m.group(1)))

    return timestamps


def summarize_execution_time(timestamps_ps):
    if not timestamps_ps:
        return {
            "has_time": False,
            "start_ps": 0,
            "end_ps": 0,
            "elapsed_ps": 0,
            "elapsed_ns": 0.0,
            "elapsed_us": 0.0,
            "elapsed_s": 0.0,
        }

    start_ps = min(timestamps_ps)
    end_ps = max(timestamps_ps)
    elapsed_ps = end_ps - start_ps

    return {
        "has_time": True,
        "start_ps": start_ps,
        "end_ps": end_ps,
        "elapsed_ps": elapsed_ps,
        "elapsed_ns": elapsed_ps / 1_000.0,
        "elapsed_us": elapsed_ps / 1_000_000.0,
        "elapsed_s": elapsed_ps / 1_000_000_000_000.0,
    }


def parse_pcie(text: str):
    rows = []

    for line in text.splitlines():
        m = pcie_tlp_re.search(line)
        if not m:
            continue

        rows.append({
            "id": int(m.group("id")),
            "payload_bytes": int(m.group("payload")),
            "packet_bytes": int(m.group("tlp_bytes")),
            "latency_ns": float(m.group("total")),
            "rc_delay_ns": float(m.group("rc")),
            "link_delay_ns": float(m.group("link")),
            "endpoint_delay_ns": float(m.group("endpoint")),
            "replay_delay_ns": float(m.group("replay")),
        })

    return rows


def parse_ucie(text: str):
    rows = []

    for line in text.splitlines():
        m = ucie_flit_re.search(line)
        if not m:
            continue

        rows.append({
            "id": int(m.group("id")),
            "payload_bytes": int(m.group("payload")),
            "packet_bytes": int(m.group("flit_bytes")),
            "latency_ns": float(m.group("total")),
            "packer_delay_ns": float(m.group("packer")),
            "d2d_delay_ns": float(m.group("d2d")),
            "phy_delay_ns": float(m.group("phy")),
            "retry_delay_ns": float(m.group("retry")),
        })

    return rows


def summarize_packets(rows, payload_filter=None):
    selected = rows

    if payload_filter is not None:
        selected = [r for r in rows if r["payload_bytes"] == payload_filter]

    if not selected:
        return {
            "count": 0,
            "avg_latency_ns": 0.0,
            "min_latency_ns": 0.0,
            "max_latency_ns": 0.0,
            "total_payload_bytes": 0,
            "total_packet_bytes": 0,
            "total_overhead_bytes": 0,
            "avg_payload_bytes": 0.0,
            "avg_packet_bytes": 0.0,
            "avg_overhead_bytes": 0.0,
            "overhead_percent": 0.0,
            "payload_efficiency_percent": 0.0,
        }

    count = len(selected)
    latencies = [r["latency_ns"] for r in selected]

    total_payload = sum(r["payload_bytes"] for r in selected)
    total_packet = sum(r["packet_bytes"] for r in selected)
    total_overhead = total_packet - total_payload

    return {
        "count": count,
        "avg_latency_ns": statistics.mean(latencies),
        "min_latency_ns": min(latencies),
        "max_latency_ns": max(latencies),
        "total_payload_bytes": total_payload,
        "total_packet_bytes": total_packet,
        "total_overhead_bytes": total_overhead,
        "avg_payload_bytes": total_payload / count,
        "avg_packet_bytes": total_packet / count,
        "avg_overhead_bytes": total_overhead / count,
        "overhead_percent": (
            100.0 * total_overhead / total_packet if total_packet else 0.0
        ),
        "payload_efficiency_percent": (
            100.0 * total_payload / total_packet if total_packet else 0.0
        ),
    }


def avg_field(rows, field):
    if not rows:
        return 0.0
    return statistics.mean(r[field] for r in rows)


def ratio(a, b):
    return a / b if b else 0.0


# ============================================================
# Load logs
# ============================================================

pcie_text = require_file(PCIE_LOG, "PCIe")
ucie_text = require_file(UCIE_LOG, "UCIe")

pcie_rows = parse_pcie(pcie_text)
ucie_rows = parse_ucie(ucie_text)

if not pcie_rows:
    raise RuntimeError(
        f"No PCIe TLP lines were parsed from {PCIE_LOG}.\n"
        f"Expected lines like:\n"
        f"PCIe TLP id=1 seq=1 payload=64 tlp_bytes=80 "
        f"rc=20ns link=150ns endpoint=50ns replay=0ns total=220ns"
    )

if not ucie_rows:
    raise RuntimeError(
        f"No UCIe Flit lines were parsed from {UCIE_LOG}.\n"
        f"Expected lines like:\n"
        f"UCIe Flit id=1 payload=64 flit_bytes=256 "
        f"packer=5ns d2d=5ns phy=2ns retry=0ns total=12ns"
    )

pcie_exec = summarize_execution_time(extract_timestamps_ps(pcie_text))
ucie_exec = summarize_execution_time(extract_timestamps_ps(ucie_text))

pcie_all = summarize_packets(pcie_rows)
ucie_all = summarize_packets(ucie_rows)

pcie_64b = summarize_packets(pcie_rows, payload_filter=64)
ucie_64b = summarize_packets(ucie_rows, payload_filter=64)

latency_ratio_64b = ratio(pcie_64b["avg_latency_ns"], ucie_64b["avg_latency_ns"])
exec_ratio = ratio(pcie_exec["elapsed_ns"], ucie_exec["elapsed_ns"])
overhead_delta_64b = ucie_64b["overhead_percent"] - pcie_64b["overhead_percent"]

pcie_avg_rc = avg_field(pcie_rows, "rc_delay_ns")
pcie_avg_link = avg_field(pcie_rows, "link_delay_ns")
pcie_avg_endpoint = avg_field(pcie_rows, "endpoint_delay_ns")
pcie_avg_replay = avg_field(pcie_rows, "replay_delay_ns")

ucie_avg_packer = avg_field(ucie_rows, "packer_delay_ns")
ucie_avg_d2d = avg_field(ucie_rows, "d2d_delay_ns")
ucie_avg_phy = avg_field(ucie_rows, "phy_delay_ns")
ucie_avg_retry = avg_field(ucie_rows, "retry_delay_ns")

# ============================================================
# Report
# ============================================================

report = f"""Final PCIe vs UCIe Comparison Report
====================================

Compared Workload
-----------------
64B accelerator workload.

Input Logs
----------
PCIe SystemC log:
{PCIE_LOG}

UCIe SystemC log:
{UCIE_LOG}

Parsed Events
-------------
PCIe parsed TLP events: {pcie_all["count"]}
UCIe parsed flit events: {ucie_all["count"]}

Important Methodology Note
--------------------------
The gem5 stats.txt file is not used for execution-time extraction in this report because the current gem5.opt run aborts before dumping normal statistics with:

fatal: Can't find port handler type 'tlm_slave'

Therefore, the execution-time metric below is a SystemC timestamp-window metric. It measures the observed TLM transaction activity from the first timestamped event to the last timestamped event in each SystemC log. It should not be presented as full gem5 CPU-cycle execution time.


1. Absolute Link / Path Latency
-------------------------------
This section compares the log-annotated path latency of generated PCIe TLPs and UCIe flits.

PCIe timing model:
PCIe latency = Root Complex delay + PCIe link delay + Endpoint delay + Replay delay

Average PCIe model components:
Root Complex delay: {pcie_avg_rc:.3f} ns
PCIe link transit delay: {pcie_avg_link:.3f} ns
Endpoint delay: {pcie_avg_endpoint:.3f} ns
Replay delay: {pcie_avg_replay:.3f} ns

Average PCIe total latency:
{pcie_avg_rc:.3f} ns + {pcie_avg_link:.3f} ns + {pcie_avg_endpoint:.3f} ns + {pcie_avg_replay:.3f} ns
= {pcie_all["avg_latency_ns"]:.3f} ns per observed TLP

UCIe timing model:
UCIe latency = Protocol/flit-packing delay + D2D adapter delay + PHY delay + Retry delay

Average UCIe model components:
Protocol/flit-packing delay: {ucie_avg_packer:.3f} ns
D2D adapter delay: {ucie_avg_d2d:.3f} ns
PHY delay: {ucie_avg_phy:.3f} ns
Retry delay: {ucie_avg_retry:.3f} ns

Average UCIe total latency:
{ucie_avg_packer:.3f} ns + {ucie_avg_d2d:.3f} ns + {ucie_avg_phy:.3f} ns + {ucie_avg_retry:.3f} ns
= {ucie_all["avg_latency_ns"]:.3f} ns per observed flit

All observed traffic:
PCIe observed TLP count: {pcie_all["count"]}
PCIe average latency: {pcie_all["avg_latency_ns"]:.3f} ns
PCIe minimum latency: {pcie_all["min_latency_ns"]:.3f} ns
PCIe maximum latency: {pcie_all["max_latency_ns"]:.3f} ns

UCIe observed flit count: {ucie_all["count"]}
UCIe average latency: {ucie_all["avg_latency_ns"]:.3f} ns
UCIe minimum latency: {ucie_all["min_latency_ns"]:.3f} ns
UCIe maximum latency: {ucie_all["max_latency_ns"]:.3f} ns

64B workload packets only:
PCIe 64B TLP count: {pcie_64b["count"]}
PCIe average 64B TLP latency: {pcie_64b["avg_latency_ns"]:.3f} ns

UCIe 64B flit count: {ucie_64b["count"]}
UCIe average 64B flit latency: {ucie_64b["avg_latency_ns"]:.3f} ns

PCIe/UCIe 64B latency ratio: {latency_ratio_64b:.3f}x

Interpretation:
The PCIe model has a larger path latency because it represents a board-level route through the Root Complex, PCIe link, and endpoint. UCIe is modeled as a package-level die-to-die interconnect with much smaller PHY delay. Therefore, the UCIe model is latency-favorable, while PCIe has the larger per-packet path latency.


2. SystemC Timestamp-Based Execution Time
-----------------------------------------
The project requests total execution time or cycles for the accelerator workload under both interconnect configurations. Since gem5 cycle statistics were unavailable, this report uses the SystemC timestamp window.

PCIe timestamp window:
First observed timestamp: {pcie_exec["start_ps"]} ps
Last observed timestamp:  {pcie_exec["end_ps"]} ps
PCIe elapsed transaction-window time: {pcie_exec["elapsed_ps"]} ps
PCIe elapsed transaction-window time: {pcie_exec["elapsed_ns"]:.6f} ns
PCIe elapsed transaction-window time: {pcie_exec["elapsed_us"]:.6f} us

UCIe timestamp window:
First observed timestamp: {ucie_exec["start_ps"]} ps
Last observed timestamp:  {ucie_exec["end_ps"]} ps
UCIe elapsed transaction-window time: {ucie_exec["elapsed_ps"]} ps
UCIe elapsed transaction-window time: {ucie_exec["elapsed_ns"]:.6f} ns
UCIe elapsed transaction-window time: {ucie_exec["elapsed_us"]:.6f} us

PCIe/UCIe timestamp-window ratio: {exec_ratio:.3f}x

Interpretation:
This metric captures the transaction window visible in the SystemC logs. If both windows are identical or nearly identical, the current TLM execution schedule is dominated by the workload generator timing rather than accumulated interconnect latency. A true CPU-cycle comparison should be added only after the gem5/TLM external port issue is fixed and stats.txt contains simTicks, simSeconds, or CPU numCycles.


3. Protocol Overhead
--------------------
This section compares UCIe 256B flit-packing and D2D adapter behavior against standard PCIe TLP routing.

PCIe overhead model:
packet size = payload bytes + 16B abstract PCIe TLP header

For one 64B PCIe TLP:
Payload = 64B
Header = 16B
Total = 80B
Overhead = 16 / 80 x 100 = 20%
Payload efficiency = 64 / 80 x 100 = 80%

UCIe overhead model:
packet size = one fixed 256B UCIe flit

For one 64B payload packed into one 256B UCIe flit:
Payload = 64B
Flit = 256B
Unused/packing overhead = 192B
Overhead = 192 / 256 x 100 = 75%
Payload efficiency = 64 / 256 x 100 = 25%

A. All observed traffic
-----------------------
This includes all parsed packet/flit events in the SystemC logs. It may include small memory-mapped bridge accesses and non-64B transactions.

PCIe all observed traffic:
Observed TLP count: {pcie_all["count"]}
Total payload bytes: {pcie_all["total_payload_bytes"]}
Total transmitted bytes: {pcie_all["total_packet_bytes"]}
Total overhead bytes: {pcie_all["total_overhead_bytes"]}
Overhead: {pcie_all["overhead_percent"]:.3f} %
Payload efficiency: {pcie_all["payload_efficiency_percent"]:.3f} %

UCIe all observed traffic:
Observed flit count: {ucie_all["count"]}
Total payload bytes: {ucie_all["total_payload_bytes"]}
Total transmitted bytes: {ucie_all["total_packet_bytes"]}
Total overhead bytes: {ucie_all["total_overhead_bytes"]}
Overhead: {ucie_all["overhead_percent"]:.3f} %
Payload efficiency: {ucie_all["payload_efficiency_percent"]:.3f} %

B. Normalized 64B workload packets only
--------------------------------------
This filters both logs to entries where payload_bytes = 64.

PCIe 64B workload traffic:
64B TLP count: {pcie_64b["count"]}
Payload bytes: {pcie_64b["total_payload_bytes"]}
Transmitted bytes: {pcie_64b["total_packet_bytes"]}
Overhead bytes: {pcie_64b["total_overhead_bytes"]}
Overhead: {pcie_64b["overhead_percent"]:.3f} %
Payload efficiency: {pcie_64b["payload_efficiency_percent"]:.3f} %

UCIe 64B workload traffic:
64B flit count: {ucie_64b["count"]}
Payload bytes: {ucie_64b["total_payload_bytes"]}
Transmitted bytes: {ucie_64b["total_packet_bytes"]}
Overhead bytes: {ucie_64b["total_overhead_bytes"]}
Overhead: {ucie_64b["overhead_percent"]:.3f} %
Payload efficiency: {ucie_64b["payload_efficiency_percent"]:.3f} %

UCIe minus PCIe 64B overhead: {overhead_delta_64b:.3f} percentage points

Interpretation:
For 64B transfers, PCIe is more byte-efficient in this model because it adds only a 16B abstract TLP header, producing an 80B packet. UCIe packs the same 64B payload into a fixed 256B flit, so unused flit capacity dominates the overhead. Therefore, the normalized 64B overhead is 20% for PCIe and 75% for UCIe.

However, UCIe overhead improves as payload size approaches the 256B flit size. For a full 256B payload, the UCIe flit is fully utilized, while PCIe still carries its header overhead. Thus, the overhead comparison depends strongly on transaction size.


Final Summary
-------------
PCIe:
- 64B TLP latency: {pcie_64b["avg_latency_ns"]:.3f} ns
- SystemC timestamp transaction window: {pcie_exec["elapsed_ns"]:.6f} ns
- 64B protocol overhead: {pcie_64b["overhead_percent"]:.3f} %
- 64B payload efficiency: {pcie_64b["payload_efficiency_percent"]:.3f} %

UCIe:
- 64B flit latency: {ucie_64b["avg_latency_ns"]:.3f} ns
- SystemC timestamp transaction window: {ucie_exec["elapsed_ns"]:.6f} ns
- 64B protocol overhead: {ucie_64b["overhead_percent"]:.3f} %
- 64B payload efficiency: {ucie_64b["payload_efficiency_percent"]:.3f} %

Main conclusion:
PCIe has higher modeled path latency due to Root Complex, board-level link, and endpoint traversal. UCIe has lower modeled die-to-die latency, but for small 64B transfers it has higher packetization overhead because the fixed 256B flit is underutilized. Therefore, PCIe is more byte-efficient for small transfers, while UCIe is latency-favorable and becomes more efficient as payload size approaches full 256B flit utilization.
"""

REPORT_OUT.write_text(report)
print(report)
print(f"\nWrote report to: {REPORT_OUT}")