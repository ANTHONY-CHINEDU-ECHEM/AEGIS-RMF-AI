# Verification and Validation Summary

* Document ID: VVR_005
* Revision: B
* Device: Aurelia P200 Ambulatory Insulin Infusion Pump
* Status: Issued with open items
* Related documents: SAS_001, HDS_002, SRS_003, UCS_004, RMP_006

This document describes a fictional device created for the Aegis RMF AI project. It is not derived from any commercial product.

## 1 Purpose

This summary lists the verification record for each requirement, the method used, the result and the test report that holds the objective evidence. It supports ISO 14971 cl 7.2, which requires verification of both the implementation and the effectiveness of every risk control measure, and ISO 13485 cl 7.3.6.

## 2 Verification records

### 2.1 Drive

* **VER_DRV_001** Verifies REQ_DRV_001. Method: Fault injection bench test. Result: PASS. Report: TR_0101.
* **VER_DRV_002** Verifies REQ_DRV_002. Method: Stall simulation bench test. Result: PASS. Report: TR_0102.
* **VER_DRV_003** Verifies REQ_DRV_003. Method: Mechanical endurance test. Result: PASS. Report: TR_0103.
* **VER_DRV_004** Verifies REQ_DRV_004. Method: Gravimetric delivery accuracy test. Result: PASS. Report: TR_0104.

### 2.2 Sensing

* **VER_SNS_001** Verifies REQ_SNS_001. Method: Sensor fault injection test. Result: PASS. Report: TR_0105.
* **VER_SNS_002** Verifies REQ_SNS_002. Method: Occlusion bench test with sensor disabled. Result: PASS. Report: TR_0106.
* **VER_SNS_003** Verifies REQ_SNS_003. Method: Occlusion bolus volume test. Result: PASS. Report: TR_0107.
* **VER_SNS_004** Verifies REQ_SNS_004. Method: Encoder fault injection test. Result: PASS. Report: TR_0108.

### 2.3 Fluid path

* **VER_RSV_001** Verifies REQ_RSV_001. Method: Pressure decay leak test. Result: PASS. Report: TR_0109.
* **VER_RSV_002** Verifies REQ_RSV_002. Method: Software verification and formative usability review. Result: PASS. Report: TR_0110.
* **VER_RSV_003** Verifies REQ_RSV_003. Method: Package integrity and sterility validation. Result: PASS. Report: TR_0111.
* **VER_INF_001** Verifies REQ_INF_001. Method: Connector engagement test. Result: PASS. Report: TR_0112.

### 2.4 Power

* **VER_PWR_001** Verifies REQ_PWR_001. Method: Battery abuse test. Result: PASS. Report: TR_0113.
* **VER_PWR_002** Verifies REQ_PWR_002. Method: Supplier audit and incoming inspection record review. Result: PASS. Report: TR_0114.
* **VER_PWR_003** Verifies REQ_PWR_003. Method: Battery discharge profile test. Result: PASS. Report: TR_0115.
* **VER_PWR_004** Verifies REQ_PWR_004. Method: Thermal chamber discharge test. Result: PASS. Report: TR_0116.
* **VER_PWR_005** Verifies REQ_PWR_005. Method: Fuel gauge fault injection test. Result: PASS. Report: TR_0117.
* **VER_PWR_006** Verifies REQ_PWR_006. Method: Charge time measurement. Result: PASS. Report: TR_0118.
* **VER_CHG_001** Verifies REQ_CHG_001. Method: Dielectric strength and leakage current test. Result: PASS. Report: TR_0119.

### 2.5 Alarm

* **VER_ALM_001** Verifies REQ_ALM_001. Method: Speaker open circuit fault test. Result: PASS. Report: TR_0120.
* **VER_ALM_002** Verifies REQ_ALM_002. Method: Alarm escalation timing test. Result: PASS. Report: TR_0121.

### 2.6 Enclosure

* **VER_ENC_001** Verifies REQ_ENC_001. Method: Drop test followed by immersion test. Result: PASS. Report: TR_0122.
* **VER_ENC_002** Verifies REQ_ENC_002. Method: Moisture sensor activation test. Result: PASS. Report: TR_0123.
* **VER_ENC_003** Verifies REQ_ENC_003. Method: Impact test and dimensional inspection. Result: PASS. Report: TR_0124.

### 2.7 Control

* **VER_MCU_001** Verifies REQ_MCU_001. Method: Firmware hang fault injection test. Result: PASS. Report: TR_0125.
* **VER_MCU_002** Verifies REQ_MCU_002. Method: Memory corruption fault injection test. Result: PASS. Report: TR_0126.
* **VER_MCU_003** Verifies REQ_MCU_003. Method: Supervisor limit test with corrupted commands. Result: PASS. Report: TR_0127.
* **VER_MCU_004** Verifies REQ_MCU_004. Method: Heartbeat loss fault injection test. Result: PASS. Report: TR_0128.

### 2.8 Therapy software

* **VER_SW_001** Verifies REQ_SW_001. Method: Software system test. Result: PASS. Report: TR_0129.
* **VER_SW_002** Verifies REQ_SW_002. Method: Software system test and summative usability evaluation. Result: PASS. Report: TR_0130.
* **VER_SW_003** Verifies REQ_SW_003. Method: Software unit and system test. Result: PASS. Report: TR_0131.
* **VER_SW_004** Verifies REQ_SW_004. Method: Software system test. Result: PASS. Report: TR_0132.
* **VER_SW_005** Verifies REQ_SW_005. Method: Software regression test. Result: FAIL. Report: TR_0133.
* **VER_SW_006** Verifies REQ_SW_006. Method: Software system test. Result: PASS. Report: TR_0134.
* **VER_SW_007** Verifies REQ_SW_007. Method: Software system test. Result: PASS. Report: TR_0135.
* **VER_SW_008** Verifies REQ_SW_008. Method: State machine model based test. Result: PASS. Report: TR_0136.
* **VER_SW_009** Verifies REQ_SW_009. Method: Communication retry fault injection test. Result: PASS. Report: TR_0137.
* **VER_SW_010** Verifies REQ_SW_010. Method: Alarm priority stress test. Result: PASS. Report: TR_0138.

### 2.9 Platform

* **VER_MEM_001** Verifies REQ_MEM_001. Method: Power interruption fault injection test. Result: PASS. Report: TR_0139.
* **VER_RTC_001** Verifies REQ_RTC_001. Method: Clock backup depletion test. Result: PASS. Report: TR_0140.

### 2.10 User interface

* **VER_UI_001** Verifies REQ_UI_001. Method: Software system test and summative usability evaluation. Result: PASS. Report: TR_0141.
* **VER_UI_002** Verifies REQ_UI_002. Method: Summative usability evaluation. Result: PASS. Report: TR_0142.
* **VER_UI_003** Verifies REQ_UI_003. Method: Alarm signal characterisation test. Result: PASS. Report: TR_0143.
* **VER_UI_004** Verifies REQ_UI_004. Method: Localisation review. Result: PASS. Report: TR_0144.

### 2.11 Connectivity

* **VER_COM_001** Verifies REQ_COM_001. Method: Penetration test. Result: PASS. Report: TR_0145.
* **VER_COM_002** Verifies REQ_COM_002. Method: Software system test. Result: PENDING. Report: TR_0146.
* **VER_COM_003** Verifies REQ_COM_003. Method: Software system test. Result: PASS. Report: TR_0147.
* **VER_COM_004** Verifies REQ_COM_004. Method: Corrupted packet injection test. Result: PASS. Report: TR_0148.
* **VER_COM_005** Verifies REQ_COM_005. Method: Software system test. Result: PASS. Report: TR_0149.
* **VER_CGM_001** Verifies REQ_CGM_001. Method: Algorithm verification with recorded sensor traces. Result: PASS. Report: TR_0150.

### 2.12 Labeling

* **VER_LBL_001** Verifies REQ_LBL_001. Method: Summative usability evaluation. Result: PASS. Report: TR_0151.
* **VER_LBL_003** Verifies REQ_LBL_003. Method: Summative usability evaluation. Result: PASS. Report: TR_0152.
* **VER_LBL_004** Verifies REQ_LBL_004. Method: Training effectiveness assessment. Result: PASS. Report: TR_0153.
* **VER_LBL_005** Verifies REQ_LBL_005. Method: Training effectiveness assessment. Result: PASS. Report: TR_0154.
* **VER_LBL_006** Verifies REQ_LBL_006. Method: Summative usability evaluation. Result: PASS. Report: TR_0155.
* **VER_LBL_007** Verifies REQ_LBL_007. Method: Software system test. Result: PASS. Report: TR_0156.
* **VER_LBL_008** Verifies REQ_LBL_008. Method: Summative usability evaluation. Result: PASS. Report: TR_0157.

## 3 Open items

Three items remain open at this revision. The regression test for REQ_SW_005 failed because the active insulin time returned to its default value after a daylight saving clock change, so insulin on board was understated for up to four hours. A corrective software change is in progress. The system test for REQ_COM_002 is pending because the companion application build that supports confirmation on the pump has not been released to the test team. No verification record exists yet for REQ_LBL_002 because the instruction on inspecting the reservoir compartment was added after the summative usability evaluation was completed.

Risk control measures that depend on these requirements must not be credited in the residual risk evaluation until the open items are closed.
