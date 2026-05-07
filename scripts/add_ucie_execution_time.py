#!/usr/bin/env python3

import re
from pathlib import Path

LOG_FILE = Path("outputs/ucie_workload_64B/run.log")
REPORT_FILE = Path("outputs/ucie_workload_64B/results/ucie_64B_latency_report.txt")
OUT_FILE = Path("outputs/ucie_workload_64B/results/ucie_64B_final_report.txt")
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

text = LOG_FILE.read_text(errors="ignore")

m = re.search(
    r"WORKLOAD_DONE\s+time_ns=([0-9.]+)\s+"
    r"workload_latency_ns=([0-9.]+)\s+"
    r"workload_cycles_at_1p5GHz=([0-9.]+)\s+"
    r"compute_latency_ns=([0-9.]+)\s+"
    r"input_writes=(\d+)\s+"
    r"output_reads=(\d+)",
    text
)

if not m:
    raise RuntimeError("Could not find WORKLOAD_DONE line in run.log")

done_time_ns = float(m.group(1))
workload_latency_ns = float(m.group(2))
workload_cycles = float(m.group(3))
compute_latency_ns = float(m.group(4))
input_writes = int(m.group(5))
output_reads = int(m.group(6))

base_report = REPORT_FILE.read_text(errors="ignore") if REPORT_FILE.exists() else ""

execution_section = f"""

Proper System Execution Time
----------------------------
The 64B UCIe workload was configured as a controlled accelerator transaction sequence:
- 16 input SRAM writes, each 64 bytes
- 1 control-register write to start computation
- status polling until computation completed
- 16 output SRAM reads, each 64 bytes

Measured workload completion time:
  {workload_latency_ns:.3f} ns

Equivalent cycles at 1.5 GHz:
  {workload_cycles:.3f} cycles

Accelerator compute latency:
  {compute_latency_ns:.3f} ns

Input writes observed:
  {input_writes}

Output reads observed:
  {output_reads}

Workload done timestamp:
  {done_time_ns:.3f} ns

Interpretation:
  Unlike the earlier fixed-limit TrafficGen run, this measurement is taken from
  the accelerator endpoint itself. The simulation stops only after the endpoint
  observes the complete workload sequence and emits WORKLOAD_DONE.
"""

OUT_FILE.write_text(base_report.rstrip() + "\n" + execution_section + "\n")

print(execution_section)
print(f"Wrote final report: {OUT_FILE}")
