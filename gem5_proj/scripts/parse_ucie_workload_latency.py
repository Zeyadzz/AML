#!/usr/bin/env python3

import re
import csv
import math
from pathlib import Path

LOG_FILE = Path("outputs/ucie_workload/run.log")
OUT_CSV = Path("outputs/ucie_workload/results/ucie_workload_latency_table.csv")
OUT_TXT = Path("outputs/ucie_workload/results/ucie_workload_metrics_report.txt")

FLIT_SIZE_BYTES = 256
THEORETICAL_UCIE_TX_NS = 10.0  # matches current HostUCIe tx_delay

time_re = re.compile(
    r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ps|ns|us|ms|s)\s+\([^)]+\)\s*:\s*(?P<msg>.*)$"
)

host_req_re = re.compile(
    r"HostUCIe nb_transport_fw received phase=BEGIN_REQ addr=(0x[0-9a-fA-F]+) len=(\d+)"
)

host_send_re = re.compile(
    r"HostUCIe Sending UCIe flit id=(\d+) addr=(0x[0-9a-fA-F]+) size=(\d+) tail=(\d+)"
)

target_recv_re = re.compile(
    r"TargetUCIe Received flit id=(\d+) payload_size=(\d+) tail=(\d+) addr=(0x[0-9a-fA-F]+)"
)

target_forward_re = re.compile(
    r"TargetUCIe Tail flit received\. Forwarding reconstructed payload to ConvAccel"
)

conv_recv_re = re.compile(
    r"ConvAccel nb_transport_fw received phase=BEGIN_REQ cmd=(\w+) addr=(0x[0-9a-fA-F]+) len=(\d+)"
)

ack_re = re.compile(
    r"HostUCIe Response extension: flit_id=(\d+) ack=(\d+) nak=(\d+)"
)

exit_tick_re = re.compile(
    r"Exit at tick (\d+), cause: (.*)"
)

def to_ps(value, unit):
    value = float(value)
    scale = {
        "ps": 1,
        "ns": 1_000,
        "us": 1_000_000,
        "ms": 1_000_000_000,
        "s": 1_000_000_000_000,
    }
    return int(value * scale[unit])

def ps_to_ns(ps):
    if ps is None:
        return None
    return ps / 1000.0

def avg(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None

def fmt(x):
    if x is None:
        return "N/A"
    return f"{x:.3f}"

if not LOG_FILE.exists():
    raise FileNotFoundError(f"Missing log file: {LOG_FILE}")

rows = {}
pending_host_reqs = []
last_target_flit_id = None
exit_tick = None
exit_cause = None

with LOG_FILE.open() as f:
    for line in f:
        exit_m = exit_tick_re.search(line)
        if exit_m:
            exit_tick = int(exit_m.group(1))
            exit_cause = exit_m.group(2).strip()

        m = time_re.match(line)
        if not m:
            continue

        t_ps = to_ps(m.group("value"), m.group("unit"))
        msg = m.group("msg")

        m_host_req = host_req_re.search(msg)
        if m_host_req:
            pending_host_reqs.append({
                "time_ps": t_ps,
                "addr": m_host_req.group(1).lower(),
                "len": int(m_host_req.group(2)),
            })
            continue

        m_send = host_send_re.search(msg)
        if m_send:
            flit_id = int(m_send.group(1))
            addr = m_send.group(2).lower()
            size = int(m_send.group(3))
            tail = int(m_send.group(4))

            host_req_time = None
            for i, req in enumerate(pending_host_reqs):
                if req["addr"] == addr and req["len"] == size:
                    host_req_time = req["time_ps"]
                    pending_host_reqs.pop(i)
                    break

            rows[flit_id] = {
                "flit_id": flit_id,
                "addr": addr,
                "payload_bytes": size,
                "tail": tail,
                "host_req_time_ps": host_req_time,
                "host_send_flit_time_ps": t_ps,
                "target_recv_flit_time_ps": None,
                "target_forward_time_ps": None,
                "conv_recv_time_ps": None,
                "ack_time_ps": None,
                "ack": 0,
                "nak": 0,
                "cmd": "",
            }
            continue

        m_target = target_recv_re.search(msg)
        if m_target:
            flit_id = int(m_target.group(1))
            last_target_flit_id = flit_id
            if flit_id in rows:
                rows[flit_id]["target_recv_flit_time_ps"] = t_ps
            continue

        if target_forward_re.search(msg):
            if last_target_flit_id in rows:
                rows[last_target_flit_id]["target_forward_time_ps"] = t_ps
            continue

        m_conv = conv_recv_re.search(msg)
        if m_conv:
            cmd = m_conv.group(1)
            addr = m_conv.group(2).lower()
            length = int(m_conv.group(3))

            for flit_id in sorted(rows):
                r = rows[flit_id]
                if (
                    r["conv_recv_time_ps"] is None
                    and r["addr"] == addr
                    and r["payload_bytes"] == length
                ):
                    r["conv_recv_time_ps"] = t_ps
                    r["cmd"] = cmd
                    break
            continue

        m_ack = ack_re.search(msg)
        if m_ack:
            flit_id = int(m_ack.group(1))
            ack = int(m_ack.group(2))
            nak = int(m_ack.group(3))

            if flit_id in rows:
                rows[flit_id]["ack_time_ps"] = t_ps
                rows[flit_id]["ack"] = ack
                rows[flit_id]["nak"] = nak
            continue

final_rows = []

for flit_id in sorted(rows):
    r = rows[flit_id]

    tx_ps = None
    accum_ps = None
    total_link_ps = None
    e2e_ps = None
    target_to_conv_ps = None
    ack_latency_ps = None

    if r["host_send_flit_time_ps"] is not None and r["target_recv_flit_time_ps"] is not None:
        tx_ps = r["target_recv_flit_time_ps"] - r["host_send_flit_time_ps"]

    if r["target_recv_flit_time_ps"] is not None and r["target_forward_time_ps"] is not None:
        accum_ps = r["target_forward_time_ps"] - r["target_recv_flit_time_ps"]

    if tx_ps is not None and accum_ps is not None:
        total_link_ps = tx_ps + accum_ps

    if r["host_req_time_ps"] is not None and r["ack_time_ps"] is not None:
        e2e_ps = r["ack_time_ps"] - r["host_req_time_ps"]

    if r["target_recv_flit_time_ps"] is not None and r["conv_recv_time_ps"] is not None:
        target_to_conv_ps = r["conv_recv_time_ps"] - r["target_recv_flit_time_ps"]

    if r["host_send_flit_time_ps"] is not None and r["ack_time_ps"] is not None:
        ack_latency_ps = r["ack_time_ps"] - r["host_send_flit_time_ps"]

    transmitted_bytes = math.ceil(r["payload_bytes"] / FLIT_SIZE_BYTES) * FLIT_SIZE_BYTES
    padding_bytes = transmitted_bytes - r["payload_bytes"]
    efficiency = r["payload_bytes"] / transmitted_bytes if transmitted_bytes else 0

    theoretical_total_ps = int(THEORETICAL_UCIE_TX_NS * 1000)
    error_percent = None
    if total_link_ps is not None:
        error_percent = ((total_link_ps - theoretical_total_ps) / theoretical_total_ps) * 100

    r.update({
        "measured_transmission_ns": ps_to_ns(tx_ps),
        "measured_accumulation_ns": ps_to_ns(accum_ps),
        "measured_total_link_ns": ps_to_ns(total_link_ps),
        "theoretical_total_link_ns": THEORETICAL_UCIE_TX_NS,
        "error_percent": error_percent,
        "target_to_conv_ns": ps_to_ns(target_to_conv_ps),
        "host_req_to_ack_ns": ps_to_ns(e2e_ps),
        "host_send_to_ack_ns": ps_to_ns(ack_latency_ps),
        "flit_size_bytes": FLIT_SIZE_BYTES,
        "transmitted_bytes": transmitted_bytes,
        "padding_bytes": padding_bytes,
        "packing_efficiency_percent": efficiency * 100,
        "packing_overhead_percent": (1 - efficiency) * 100,
    })

    final_rows.append(r)

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

fieldnames = [
    "flit_id",
    "cmd",
    "addr",
    "payload_bytes",
    "flit_size_bytes",
    "transmitted_bytes",
    "padding_bytes",
    "packing_efficiency_percent",
    "packing_overhead_percent",
    "ack",
    "nak",
    "measured_transmission_ns",
    "measured_accumulation_ns",
    "measured_total_link_ns",
    "theoretical_total_link_ns",
    "error_percent",
    "target_to_conv_ns",
    "host_send_to_ack_ns",
    "host_req_to_ack_ns",
]

with OUT_CSV.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(final_rows)

tx_avg = avg([r["measured_transmission_ns"] for r in final_rows])
accum_avg = avg([r["measured_accumulation_ns"] for r in final_rows])
total_avg = avg([r["measured_total_link_ns"] for r in final_rows])
e2e_avg = avg([r["host_req_to_ack_ns"] for r in final_rows])
target_conv_avg = avg([r["target_to_conv_ns"] for r in final_rows])

total_flits = len(final_rows)
ack_count = sum(r["ack"] for r in final_rows)
nak_count = sum(r["nak"] for r in final_rows)
payload_total = sum(r["payload_bytes"] for r in final_rows)
transmitted_total = sum(r["transmitted_bytes"] for r in final_rows)
padding_total = sum(r["padding_bytes"] for r in final_rows)
eff_total = (payload_total / transmitted_total * 100) if transmitted_total else 0
overhead_total = 100 - eff_total

report = f"""
UCIe Metrics Report
===================

1. Absolute Link Latency
------------------------
Average measured transmission time:
  {fmt(tx_avg)} ns

Average measured accumulation time:
  {fmt(accum_avg)} ns

Average measured total UCIe link latency:
  {fmt(total_avg)} ns

Theoretical total link latency used for this model:
  {THEORETICAL_UCIE_TX_NS:.3f} ns

Average TargetUCIe-to-ConvAccel forwarding latency:
  {fmt(target_conv_avg)} ns

Average host request to ACK latency:
  {fmt(e2e_avg)} ns


2. System Execution Time
------------------------
Current run completion tick:
  {exit_tick if exit_tick is not None else "N/A"}

Exit cause:
  {exit_cause if exit_cause else "N/A"}

Note:
  This run uses TrafficGen and exits at a fixed simulation limit.
  Therefore, this is a structural/protocol validation run, not yet a final
  accelerator workload execution-time measurement.


3. Protocol Overhead
--------------------
UCIe flit size:
  {FLIT_SIZE_BYTES} bytes

Total flits observed:
  {total_flits}

ACK count:
  {ack_count}

NAK count:
  {nak_count}

Total payload bytes:
  {payload_total} bytes

Total transmitted bytes assuming 256B flits:
  {transmitted_total} bytes

Total padding bytes:
  {padding_total} bytes

Overall packing efficiency:
  {eff_total:.2f} %

Overall packing overhead:
  {overhead_total:.2f} %

Interpretation:
  The current TrafficGen accesses are mostly 4-byte transactions.
  Each 4-byte access still occupies one 256-byte UCIe flit, so padding
  overhead is expected to be high. This is useful for protocol validation,
  but larger accelerator buffer transfers are needed for realistic efficiency.
"""

OUT_TXT.write_text(report.strip() + "\n")

print(report)
print(f"\nWrote CSV: {OUT_CSV}")
print(f"Wrote report: {OUT_TXT}")