# UCIe Final Deliverables Report

## Scope

This report summarizes the current **UCIe-only** implementation. The PCIe path is not implemented yet, so PCIe comparison fields are marked as pending.

Implemented path:

```text
gem5 TrafficGen
  -> ExternalSlave / Gem5SlaveTransactor
  -> HostUCIe
  -> TargetUCIe
  -> ConvAccel
  -> response path back
```

The workload is a controlled TrafficGen accelerator workload using 64-byte SRAM accesses, a control-register write, status polling, and output reads.

---

## 1. Absolute Link Latency

| Metric | UCIe measured | UCIe theoretical/model target |
|---|---:|---:|
| Average transmission time | 10.000 ns | 10.000 ns |
| Average accumulation time | 0.000 ns | 0.000 ns |
| Average total link latency | 10.000 ns | 10.000 ns |
| Average ACK latency from flit send | 10.000 ns | Model-dependent |
| Latency error vs theoretical | 0.000 % | 0% ideal |

### Interpretation

The measured UCIe link latency is dominated by the configured HostUCIe transmission delay. Accumulation time is approximately zero in this run because each TrafficGen access fits into one UCIe flit and TargetUCIe forwards reconstructed payloads immediately.

---

## 2. System Execution Time

| Metric | UCIe workload result |
|---|---:|
| Workload start timestamp | 17.337 ns |
| Compute start timestamp | 1017.170 ns |
| Compute done timestamp | 2297.170 ns |
| Workload completion timestamp | 5092.540 ns |
| Workload latency | 5075.203 ns |
| Equivalent cycles at 1.5 GHz | 7612.805 cycles |
| Accelerator compute latency | 1280.000 ns |
| Input SRAM writes observed | 16 |
| Output SRAM reads observed | 16 |
| Simulation stop tick | N/A |
| Exit cause | N/A |

### Interpretation

The workload execution time is taken from the `WORKLOAD_DONE` event emitted by `ConvAccel`, not simply from a fixed simulation limit. This makes it a workload-level timing result for the UCIe-controlled accelerator transaction sequence.

The equivalent cycle count is computed using the configured gem5 clock:

```text
Clock frequency = 1.5 GHz
Cycle time = 1 / 1.5 GHz
Execution cycles = workload_latency_ns x 1.5
```

---

## 3. Protocol Overhead

| Metric | UCIe result |
|---|---:|
| UCIe flit size | 256 bytes |
| Total flits observed | 632 |
| ACK count | 632 |
| NAK count | 0 |
| Total payload bytes | 4448 bytes |
| Total transmitted bytes | 161792 bytes |
| Total padding bytes | 157344 bytes |
| Packing efficiency | 2.749 % |
| Packing overhead | 97.251 % |

### Interpretation

The 64-byte workload improves UCIe flit utilization compared to the earlier 4-byte workload, but each 64-byte transaction still occupies one 256-byte UCIe flit. Therefore, ideal efficiency for the SRAM transfers is approximately:

```text
64 bytes / 256 bytes = 25%
```

Control and status accesses remain 4-byte transactions, so the measured total efficiency may be slightly lower than the SRAM-only ideal.

---

## Current Completion Status

| Required deliverable | UCIe status | PCIe status |
|---|---|---|
| Absolute Link Latency | Complete for UCIe | Pending |
| System Execution Time | Complete for UCIe controlled workload | Pending |
| Protocol Overhead | Complete for UCIe | Pending |
| PCIe vs UCIe comparison | Pending | Pending |

---

## Files Used

- Input log: `outputs/ucie_workload_64B/run.log`
- Output report: `outputs/ucie_workload_64B/results/ucie_final_deliverables_report.md`
