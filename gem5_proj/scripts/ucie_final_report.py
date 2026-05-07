#!/usr/bin/env python3

import re
import math
from pathlib import Path

LOG = Path("outputs/ucie_workload_64B/run.log")
OUT = Path("outputs/ucie_workload_64B/results/simple_ucie_report.md")

FLIT_SIZE = 256
THEORETICAL_LINK_NS = 10.0

OUT.parent.mkdir(parents=True, exist_ok=True)

def time_to_ns(value, unit):
    value = float(value)
    scale = {
        "ps": 0.001,
        "ns": 1.0,
        "us": 1000.0,
        "ms": 1_000_000.0,
        "s": 1_000_000_000.0,
    }
    return value * scale[unit]

def fmt(x, unit=""):
    return "N/A" if x is None else f"{x:.3f}{unit}"

time_re = re.compile(r"^\s*([0-9.]+)\s*(ps|ns|us|ms|s)\s+\([^)]+\)\s*:\s*(.*)$")

send_re = re.compile(
    r"HostUCIe Sending UCIe flit id=(\d+).*size=(\d+)"
)

recv_re = re.compile(
    r"TargetUCIe Received flit id=(\d+).*payload_size=(\d+)"
)

ack_re = re.compile(
    r"HostUCIe Response extension: flit_id=(\d+) ack=(\d+) nak=(\d+)"
)

done_re = re.compile(
    r"WORKLOAD_DONE.*"
    r"workload_latency_ns=([0-9.]+).*"
    r"workload_cycles_at_1p5GHz=([0-9.]+).*"
    r"compute_latency_ns=([0-9.]+).*"
    r"input_writes=(\d+).*"
    r"output_reads=(\d+)"
)

if not LOG.exists():
    raise FileNotFoundError(f"Missing log file: {LOG}")

send_time = {}
recv_time = {}
payload_size = {}

ack_count = 0
nak_count = 0

workload_latency_ns = None
workload_cycles = None
compute_latency_ns = None
input_writes = None
output_reads = None

for line in LOG.read_text(errors="ignore").splitlines():
    m_done = done_re.search(line)
    if m_done:
        workload_latency_ns = float(m_done.group(1))
        workload_cycles = float(m_done.group(2))
        compute_latency_ns = float(m_done.group(3))
        input_writes = int(m_done.group(4))
        output_reads = int(m_done.group(5))

    m_time = time_re.match(line)
    if not m_time:
        continue

    t_ns = time_to_ns(m_time.group(1), m_time.group(2))
    msg = m_time.group(3)

    m_send = send_re.search(msg)
    if m_send:
        flit_id = int(m_send.group(1))
        send_time[flit_id] = t_ns
        payload_size[flit_id] = int(m_send.group(2))
        continue

    m_recv = recv_re.search(msg)
    if m_recv:
        flit_id = int(m_recv.group(1))
        recv_time[flit_id] = t_ns
        payload_size[flit_id] = int(m_recv.group(2))
        continue

    m_ack = ack_re.search(msg)
    if m_ack:
        ack_count += int(m_ack.group(2))
        nak_count += int(m_ack.group(3))

latencies = []
for flit_id, t_send in send_time.items():
    if flit_id in recv_time:
        latencies.append(recv_time[flit_id] - t_send)

avg_link_latency_ns = sum(latencies) / len(latencies) if latencies else None

latency_error_percent = None
if avg_link_latency_ns is not None:
    latency_error_percent = (
        (avg_link_latency_ns - THEORETICAL_LINK_NS)
        / THEORETICAL_LINK_NS
    ) * 100.0

payload_total = sum(payload_size.values())
transmitted_total = sum(
    math.ceil(size / FLIT_SIZE) * FLIT_SIZE
    for size in payload_size.values()
)

padding_total = transmitted_total - payload_total

packing_efficiency = (
    (payload_total / transmitted_total) * 100.0
    if transmitted_total else 0.0
)

packing_overhead = 100.0 - packing_efficiency

report = f"""# UCIe Workload Report

## 1. Absolute Link Latency

| Metric | Value |
|---|---:|
| Average measured UCIe link latency | {fmt(avg_link_latency_ns, " ns")} |
| Theoretical/model UCIe link latency | {THEORETICAL_LINK_NS:.3f} ns |
| Error vs theoretical | {fmt(latency_error_percent, " %")} |

## 2. System Execution Time

| Metric | Value |
|---|---:|
| Workload latency | {fmt(workload_latency_ns, " ns")} |
| Equivalent cycles at 1.5 GHz | {fmt(workload_cycles, " cycles")} |
| Accelerator compute latency | {fmt(compute_latency_ns, " ns")} |
| Input writes observed | {input_writes if input_writes is not None else "N/A"} |
| Output reads observed | {output_reads if output_reads is not None else "N/A"} |

## 3. Protocol Overhead

| Metric | Value |
|---|---:|
| UCIe flit size | {FLIT_SIZE} bytes |
| Total flits observed | {len(payload_size)} |
| ACK count | {ack_count} |
| NAK count | {nak_count} |
| Total payload bytes | {payload_total} bytes |
| Total transmitted bytes | {transmitted_total} bytes |
| Total padding bytes | {padding_total} bytes |
| Packing efficiency | {packing_efficiency:.3f}% |
| Packing overhead | {packing_overhead:.3f}% |

## Notes

This report is for the current UCIe-only controlled TrafficGen accelerator workload.
PCIe comparison is still pending.
"""

OUT.write_text(report)
print(report)
print(f"\nWrote: {OUT}")