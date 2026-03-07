# Lab 2 – 32-bit ALU Design Using Bambu HLS and Librelane ASIC Flow

## Overview

This lab demonstrates the design and implementation of a **32-bit Arithmetic Logic Unit (ALU)** using a high-level synthesis (HLS) and ASIC design flow.

The ALU was first described in **C/C++** and synthesized to RTL using **Bambu HLS**. The generated RTL was then processed through the **Librelane ASIC flow** to perform synthesis, placement, routing, and physical design.

This lab illustrates a **complete hardware design flow**, from high-level description to ASIC layout generation.

---

## Design Flow

The project follows the workflow below:

1. **High-Level Design**

   * The ALU functionality is implemented in C/C++.

2. **High-Level Synthesis (HLS)**

   * Bambu HLS converts the C/C++ description into synthesizable Verilog.

3. **RTL Generation**

   * The generated Verilog describes the hardware implementation of the ALU.

4. **ASIC Implementation**

   * The RTL is processed using the Librelane flow to perform:

     * Logic synthesis
     * Floorplanning
     * Placement
     * Routing
     * Timing analysis

5. **Final Layout**

   * The final output is a **GDSII layout** representing the physical implementation of the ALU.

---

## ALU Description

The implemented ALU operates on **32-bit operands** and supports several arithmetic and logical operations.

### Supported Operations

| Opcode | Operation     |
| ------ | ------------- |
| 000    | Addition      |
| 001    | Subtraction   |
| 010    | Bitwise AND   |
| 011    | Bitwise OR    |
| 100    | Bitwise XOR   |
| 101    | Shift Left    |
| 110    | Shift Right   |

### Inputs

* `A` – 32-bit operand
* `B` – 32-bit operand
* `opcode` – operation selector

### Output

* `result` – 32-bit computation result

---

## Tools Used

| Tool          | Purpose                            |
| ------------- | ---------------------------------- |
| **Bambu HLS** | High-level synthesis (C/C++ → RTL) |
| **Librelane** | Open-source ASIC design flow       |
| **Verilog**   | Hardware description language      |
| **GTKWave**   | Waveform visualization             |

---
