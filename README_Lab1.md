# Lab 1 – Deploying the ML Zoo Keyword Spotting Model on Zynq SoC

## Overview

This lab demonstrates the deployment of a **Speech recognition** model from the ML Zoo on a **Xilinx Zynq SoC (ZedBoard)**.
The goal is to evaluate two system configurations:

1. **Processing System (PS) Only** – the entire neural network runs on the ARM processor.
2. **PS + Hardware Accelerator (PL)** – the convolution layer is offloaded to a custom hardware accelerator implemented in programmable logic.

This experiment highlights the **performance benefits of hardware/software co-design** for machine learning workloads on embedded systems.

---

## System Architecture

### PS-Only Implementation

* The ARM Cortex-A9 processor executes the entire neural network.
* All convolution, activation, and inference logic run in software.
* The model parameters are stored in memory and processed sequentially.

**Characteristics**

* Simpler design
* No FPGA hardware acceleration
* Higher computation latency

---

### PS + PL Accelerator Implementation

* The convolution operation is offloaded to a **custom hardware accelerator** implemented in the FPGA fabric.
* The ARM processor coordinates the computation and handles the remaining layers.
* Communication between PS and PL is done through **AXI interfaces**.

**Characteristics**

* Convolution executed in hardware
* Reduced inference time
* Demonstrates HW/SW co-design principles

---

## Model Description

The deployed model is the **ML Zoo Keyword Spotting model** designed for speech command recognition.

**Model Features**

* Input: Quantized audio feature vector (`int8`)
* Task: Classify spoken keywords
* Dataset: Speech Commands dataset
* Output: Probability scores for each keyword class

The inference pipeline consists of:

1. Feature extraction (audio preprocessing)
2. Convolution layer
3. Activation (ReLU)
4. Classification

---

## Hardware Platform

* **Board:** ZedBoard
* **SoC:** Xilinx Zynq-7000
* **Processor:** ARM Cortex-A9 (PS)
* **Programmable Logic:** FPGA fabric (PL)

---

## Hardware Accelerator

The hardware accelerator implements the **convolution (MAC) operation** of the neural network.

**Key components**

* Convolution datapath
* Multiply–Accumulate units
* AXI interface for communication with the PS
* Control signals for start/done synchronization

The PS triggers the accelerator and reads the result once computation completes.


