# System Architecture Specification

* Document ID: SAS_001
* Revision: E
* Device: Aurelia P200 Ambulatory Insulin Infusion Pump
* Status: Released for design verification
* Related documents: HDS_002, SRS_003, UCS_004, VVR_005, RMP_006

This document describes a fictional device created for the Aegis RMF AI project. It is not derived from any commercial product.

## 1 Purpose and scope

This specification defines the architecture of the Aurelia P200, the decomposition of the device into components and the allocation of safety functions to those components. It is the entry point for risk analysis under ISO 14971 cl 5.1 because every hazard analysis record must trace to a component named here.

## 2 Intended use

The Aurelia P200 is intended for the continuous subcutaneous delivery of U100 rapid acting insulin, at set and variable rates, for the management of diabetes mellitus in persons aged six years and older who require insulin. The pump is intended for use at home, at work, at school and during travel by patients and caregivers who have completed the structured training programme. The pump is worn on the body for 24 hours a day, including during sleep and exercise.

Reasonably foreseeable misuse considered under ISO 14971 cl 5.2 includes wearing an infusion set beyond its labeled interval, charging the pump from a damaged power source, carrying the pump unlocked in a pocket, dosing on a glucose value without checking its age and operation by an untrained caregiver.

## 3 System overview

The pump is built around two processors. The main controller runs the therapy applications, the user interface and the communication stack. The safety supervisor is an independent processor that owns the motor power switch and monitors delivery against limits that the main controller cannot change. This separation means that no single fault in the main controller can cause sustained overdelivery.

Insulin is held in a single use reservoir and is displaced by a plunger driven through a lead screw by a geared stepper motor. A rotary encoder measures actual motor rotation and a force sensor measures the load on the plunger so that both overdelivery and blocked delivery can be detected. A lithium battery pack powers the system and a fuel gauge estimates remaining capacity. Alarms are annunciated by display, speaker and vibration motor. A Bluetooth low energy radio connects the pump to a companion phone application and to a continuous glucose sensor.

Characteristics related to safety identified under ISO 14971 cl 5.3 include delivery accuracy, maximum single fault overdelivery volume, occlusion detection time, alarm audibility, battery reserve for alarms, ingress protection and the integrity of therapy settings.

## 4 Component inventory

* **CMP_DRV_01** Stepper Motor Drive Assembly. Subsystem: Drive. Specified in: HDS_002 section 3.1. Software safety class: not applicable.
* **CMP_DRV_02** Lead Screw and Plunger Coupling. Subsystem: Drive. Specified in: HDS_002 section 3.2. Software safety class: not applicable.
* **CMP_SNS_01** Occlusion Force Sensor. Subsystem: Sensing. Specified in: HDS_002 section 4.1. Software safety class: not applicable.
* **CMP_SNS_02** Motor Rotary Encoder. Subsystem: Sensing. Specified in: HDS_002 section 4.2. Software safety class: not applicable.
* **CMP_RSV_01** Insulin Reservoir and Seal. Subsystem: Fluid path. Specified in: HDS_002 section 5.1. Software safety class: not applicable.
* **CMP_INF_01** Infusion Set Connector. Subsystem: Fluid path. Specified in: HDS_002 section 5.2. Software safety class: not applicable.
* **CMP_PWR_01** Lithium Battery Pack. Subsystem: Power. Specified in: HDS_002 section 6.1. Software safety class: not applicable.
* **CMP_PWR_02** Battery Fuel Gauge. Subsystem: Power. Specified in: HDS_002 section 6.2. Software safety class: not applicable.
* **CMP_CHG_01** Charging Circuit. Subsystem: Power. Specified in: HDS_002 section 6.3. Software safety class: not applicable.
* **CMP_ALM_01** Audible and Vibratory Alarm Hardware. Subsystem: Alarm. Specified in: HDS_002 section 7.1. Software safety class: not applicable.
* **CMP_ENC_01** Enclosure and Ingress Protection. Subsystem: Enclosure. Specified in: HDS_002 section 7.2. Software safety class: not applicable.
* **CMP_ACC_01** Belt Clip and Holster. Subsystem: Accessory. Specified in: HDS_002 section 7.3. Software safety class: not applicable.
* **CMP_MCU_01** Main Controller Firmware Platform. Subsystem: Control. Specified in: SRS_003 section 3.1. Software safety class: Class C.
* **CMP_MCU_02** Safety Supervisor Processor. Subsystem: Control. Specified in: SRS_003 section 3.2. Software safety class: Class C.
* **CMP_SW_01** Dose Calculation Software. Subsystem: Therapy software. Specified in: SRS_003 section 4.1. Software safety class: Class C.
* **CMP_SW_02** Delivery Control Software. Subsystem: Therapy software. Specified in: SRS_003 section 4.2. Software safety class: Class C.
* **CMP_SW_03** Alarm Manager Software. Subsystem: Therapy software. Specified in: SRS_003 section 4.3. Software safety class: Class C.
* **CMP_MEM_01** Nonvolatile Settings Memory. Subsystem: Platform. Specified in: SRS_003 section 5.1. Software safety class: Class C.
* **CMP_RTC_01** Real Time Clock. Subsystem: Platform. Specified in: SRS_003 section 5.2. Software safety class: Class B.
* **CMP_UI_01** Touchscreen and Keypad. Subsystem: User interface. Specified in: UCS_004 section 3.1. Software safety class: not applicable.
* **CMP_COM_01** Bluetooth Communication Module. Subsystem: Connectivity. Specified in: UCS_004 section 4.1. Software safety class: Class C.
* **CMP_CGM_01** Glucose Sensor Data Interface. Subsystem: Connectivity. Specified in: UCS_004 section 4.2. Software safety class: Class C.
* **CMP_LBL_01** Labeling and Instructions for Use. Subsystem: Labeling. Specified in: UCS_004 section 5.1. Software safety class: not applicable.

## 5 Safety architecture principles

The design applies the priority order of ISO 14971 cl 7.1. Hazards are first removed or reduced by inherently safe design, such as the positive locking plunger coupling and the fixed decimal dose entry format. Protective measures follow, such as the independent delivery limit of the safety supervisor and the staged battery alarms. Information for safety, such as training on infusion site checks, is used only as a supplement and is never the sole control for a risk that could cause death or permanent injury.

Every protective measure that depends on software is allocated to a Class C software item under IEC 62304 cl 4.3 and is traced to a software requirement in SRS_003 and to a verification record in VVR_005.
