#!/usr/bin/env python3

from pathlib import Path
import re
import csv

OUT_DIR = Path("outputs/pcie_workload_64B")
RESULTS_DIR = OUT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

SYSTEMC_LOG = OUT_DIR / "systemc_pcie.log"

CSV_OUT = RESULTS_DIR / "pcie_64B_latency_table.csv"
REPORT_OUT = RESULTS_DIR / "pcie_64B_final_report.txt"

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

if not SYSTEMC_LOG.exists():
    raise FileNotFoundError(f"Missing SystemC PCIe log: {SYSTEMC_LOG}")

rows = []
timestamps_ps = []

for line in SYSTEMC_LOG.read_text(errors="ignore").splitlines():
    ts = timestamp_re.search(line)
    if ts:
        timestamps_ps.append(int(ts.group(1)))

    m = pcie_tlp_re.search(line)
    if m:
        rows.append({
            "tlp_id": int(m.group("id")),
            "seq_num": int(m.group("seq")),
            "payload_bytes": int(m.group("payload")),
            "tlp_bytes": int(m.group("tlp_bytes")),
            "rc_delay_ns": float(m.group("rc")),
            "link_delay_ns": float(m.group("link")),
            "endpoint_delay_ns": float(m.group("endpoint")),
            "replay_delay_ns": float(m.group("replay")),
            "total_link_latency_ns": float(m.group("total")),
        })


def summarize_tlps(selected_rows):
    if not selected_rows:
        return {
            "count": 0,
            "avg_latency_ns": 0.0,
            "min_latency_ns": 0.0,
            "max_latency_ns": 0.0,
            "avg_rc_ns": 0.0,
            "avg_link_ns": 0.0,
            "avg_endpoint_ns": 0.0,
            "avg_replay_ns": 0.0,
            "total_payload_bytes": 0,
            "total_tlp_bytes": 0,
            "total_overhead_bytes": 0,
            "avg_payload_bytes": 0.0,
            "avg_tlp_bytes": 0.0,
            "avg_overhead_bytes": 0.0,
            "overhead_percent": 0.0,
            "payload_efficiency_percent": 0.0,
        }

    count = len(selected_rows)

    total_payload_bytes = sum(r["payload_bytes"] for r in selected_rows)
    total_tlp_bytes = sum(r["tlp_bytes"] for r in selected_rows)
    total_overhead_bytes = total_tlp_bytes - total_payload_bytes

    return {
        "count": count,
        "avg_latency_ns": sum(r["total_link_latency_ns"] for r in selected_rows) / count,
        "min_latency_ns": min(r["total_link_latency_ns"] for r in selected_rows),
        "max_latency_ns": max(r["total_link_latency_ns"] for r in selected_rows),
        "avg_rc_ns": sum(r["rc_delay_ns"] for r in selected_rows) / count,
        "avg_link_ns": sum(r["link_delay_ns"] for r in selected_rows) / count,
        "avg_endpoint_ns": sum(r["endpoint_delay_ns"] for r in selected_rows) / count,
        "avg_replay_ns": sum(r["replay_delay_ns"] for r in selected_rows) / count,
        "total_payload_bytes": total_payload_bytes,
        "total_tlp_bytes": total_tlp_bytes,
        "total_overhead_bytes": total_overhead_bytes,
        "avg_payload_bytes": total_payload_bytes / count,
        "avg_tlp_bytes": total_tlp_bytes / count,
        "avg_overhead_bytes": total_overhead_bytes / count,
        "overhead_percent": (
            100.0 * total_overhead_bytes / total_tlp_bytes
            if total_tlp_bytes else 0.0
        ),
        "payload_efficiency_percent": (
            100.0 * total_payload_bytes / total_tlp_bytes
            if total_tlp_bytes else 0.0
        ),
    }


all_summary = summarize_tlps(rows)

# Workload-only view: only the intended 64-byte TLPs.
workload_64b_rows = [r for r in rows if r["payload_bytes"] == 64]
workload_summary = summarize_tlps(workload_64b_rows)

# Execution time from SystemC timestamps.
if timestamps_ps:
    start_ps = min(timestamps_ps)
    end_ps = max(timestamps_ps)
    execution_time_ps = end_ps - start_ps
else:
    start_ps = 0
    end_ps = 0
    execution_time_ps = 0

execution_time_ns = execution_time_ps / 1_000.0
execution_time_us = execution_time_ps / 1_000_000.0
execution_time_s = execution_time_ps / 1_000_000_000_000.0

# Write full latency CSV.
with CSV_OUT.open("w", newline="") as f:
    fieldnames = [
        "tlp_id",
        "seq_num",
        "payload_bytes",
        "tlp_bytes",
        "rc_delay_ns",
        "link_delay_ns",
        "endpoint_delay_ns",
        "replay_delay_ns",
        "total_link_latency_ns",
    ]

    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

report = f"""PCIe 64B Final Deliverables Report
==================================

Input Log
---------
SystemC PCIe log:
{SYSTEMC_LOG}

Generated Files
---------------
Latency CSV:
{CSV_OUT}

Final report:
{REPORT_OUT}


1. Absolute Link Latency
------------------------
The PCIe model reports one latency entry per generated PCIe Transaction Layer Packet (TLP).

The current latency model is:

Total PCIe latency = Root Complex delay + PCIe link delay + Endpoint delay + Replay delay

Model parameters:
Root Complex delay: {all_summary["avg_rc_ns"]:.3f} ns
PCIe link transit delay: {all_summary["avg_link_ns"]:.3f} ns
Endpoint delay: {all_summary["avg_endpoint_ns"]:.3f} ns
Replay delay: {all_summary["avg_replay_ns"]:.3f} ns

All observed PCIe TLPs:
Observed TLP count: {all_summary["count"]}
Average total PCIe link latency per TLP: {all_summary["avg_latency_ns"]:.3f} ns
Minimum total PCIe link latency per TLP: {all_summary["min_latency_ns"]:.3f} ns
Maximum total PCIe link latency per TLP: {all_summary["max_latency_ns"]:.3f} ns

64B workload TLPs only:
Observed 64B TLP count: {workload_summary["count"]}
Average total PCIe link latency per 64B TLP: {workload_summary["avg_latency_ns"]:.3f} ns
Minimum total PCIe link latency per 64B TLP: {workload_summary["min_latency_ns"]:.3f} ns
Maximum total PCIe link latency per 64B TLP: {workload_summary["max_latency_ns"]:.3f} ns


2. System Execution Time
------------------------
The gem5 stats.txt file was not used for execution time because the gem5.opt run aborted before dumping statistics due to the external TLM handler issue:

fatal: Can't find port handler type 'tlm_slave'

Therefore, execution time is extracted from the SystemC transaction log timestamps.

First observed SystemC timestamp: {start_ps} ps
Last observed SystemC timestamp:  {end_ps} ps

Total timestamp-based execution time: {execution_time_ps} ps
Total timestamp-based execution time: {execution_time_ns:.6f} ns
Total timestamp-based execution time: {execution_time_us:.6f} us
Total timestamp-based execution time: {execution_time_s:.12e} s


3. Protocol Overhead
--------------------
The report gives two overhead views:

A. All observed PCIe traffic
This includes all TLPs present in the SystemC log, including small bridge/control transactions.

Observed TLP count: {all_summary["count"]}
Average payload bytes per TLP: {all_summary["avg_payload_bytes"]:.3f} bytes
Average total TLP bytes: {all_summary["avg_tlp_bytes"]:.3f} bytes
Average overhead bytes per TLP: {all_summary["avg_overhead_bytes"]:.3f} bytes

Total payload bytes transmitted: {all_summary["total_payload_bytes"]}
Total TLP bytes transmitted: {all_summary["total_tlp_bytes"]}
Total protocol overhead bytes: {all_summary["total_overhead_bytes"]}

Protocol overhead percentage: {all_summary["overhead_percent"]:.3f} %
Payload efficiency: {all_summary["payload_efficiency_percent"]:.3f} %

B. 64B workload TLPs only
This filters the log to TLPs where payload_bytes = 64.

Observed 64B TLP count: {workload_summary["count"]}
Average payload bytes per 64B TLP: {workload_summary["avg_payload_bytes"]:.3f} bytes
Average total TLP bytes per 64B TLP: {workload_summary["avg_tlp_bytes"]:.3f} bytes
Average overhead bytes per 64B TLP: {workload_summary["avg_overhead_bytes"]:.3f} bytes

Total 64B workload payload bytes: {workload_summary["total_payload_bytes"]}
Total 64B workload TLP bytes: {workload_summary["total_tlp_bytes"]}
Total 64B workload overhead bytes: {workload_summary["total_overhead_bytes"]}

64B workload protocol overhead percentage: {workload_summary["overhead_percent"]:.3f} %
64B workload payload efficiency: {workload_summary["payload_efficiency_percent"]:.3f} %

Overhead Formula
----------------
Protocol overhead percentage = overhead bytes / total TLP bytes × 100

For each ideal 64B PCIe TLP in the current model:

Payload = 64 bytes
Header = 16 bytes
Total TLP size = 80 bytes

Protocol overhead = 16 / 80 × 100 = 20.000 %
Payload efficiency = 64 / 80 × 100 = 80.000 %


Summary
-------
The PCIe 64B run produced {all_summary["count"]} total observed TLPs in the SystemC log.
Out of these, {workload_summary["count"]} TLPs carried the intended 64-byte workload payload.

Average absolute PCIe latency was {all_summary["avg_latency_ns"]:.3f} ns per observed TLP.
Average absolute PCIe latency for 64B workload TLPs was {workload_summary["avg_latency_ns"]:.3f} ns per TLP.

Timestamp-based system execution time was {execution_time_ns:.6f} ns.

Overall observed traffic overhead was {all_summary["overhead_percent"]:.3f} %.
For the intended 64B workload TLPs, protocol overhead was {workload_summary["overhead_percent"]:.3f} %.
"""

REPORT_OUT.write_text(report)
print(report)