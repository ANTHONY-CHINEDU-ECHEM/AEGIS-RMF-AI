# Hardware Design Specification

* Document ID: HDS_002
* Revision: D
* Device: Aurelia P200 Ambulatory Insulin Infusion Pump
* Status: Released for design verification
* Related documents: SAS_001, VVR_005, RMP_006

This document describes a fictional device created for the Aegis RMF AI project. It is not derived from any commercial product.

## 1 Purpose

This specification defines the hardware components of the Aurelia P200, their requirements and the design failure considerations identified by the hardware engineering team.

## 2 Conventions

Requirements carry the identifier prefix REQ and are verified by the records listed in VVR_005. Design failure considerations carry the prefix DFC and record, for each foreseeable failure of a component, the failure mode, its cause, the hazard, the hazardous situation, the harm, the means of detection and the estimated occurrence before risk controls, followed by the risk control measures that address it. Each risk control line lists the control identifier, its description, its type under ISO 14971 cl 7.1, the claimed reduction in rating levels and the requirements that implement it.

## 3 Drive Subsystem

The drive subsystem moves the reservoir plunger. Failures here act directly on the delivered dose.

### 3.1 Stepper Motor Drive Assembly (CMP_DRV_01)

The drive assembly converts delivery commands from the delivery control software into plunger travel. A two phase stepper motor is driven through an H bridge stage and a 256 to 1 planetary gear train. One motor step corresponds to 0.0005 units of U100 insulin. Motor power is routed through a series switch that only the safety supervisor can close.

**Requirements**

* **REQ_DRV_001** The safety supervisor shall remove motor drive power within 100 milliseconds when measured encoder counts exceed commanded steps by more than 2 percent. [Verified by: VER_DRV_001] [Standards: IEC 62304 cl 7.2; IEC 60601 1 cl 4.2]
* **REQ_DRV_002** The pump shall detect the absence of plunger advance within three commanded delivery pulses and raise a high priority no delivery alarm. [Verified by: VER_DRV_002] [Standards: IEC 60601 1 8 cl 6.1]

**Design failure considerations**

#### DFC_DRV_01 Continuous motor run from a shorted driver stage

* Failure mode: Motor driver stage fails short and the motor runs continuously
* Cause: Short circuit failure of a transistor in the H bridge driver stage
* Hazard: Overdelivery of insulin
* Hazardous situation: The pump delivers insulin continuously beyond the programmed dose while the patient is unaware
* Harm: Severe hypoglycemia with loss of consciousness
* Detection before controls: No detection
* Occurrence before controls: Remote
* Risk control: RCM_DRV_01 | Independent motor power cutoff by the safety supervisor when encoder counts exceed commanded steps | protective measure | occurrence 1, detectability 3 | REQ_DRV_001
* Risk control: RCM_MCU_03 | Independent hourly delivery limit enforced by the safety supervisor | protective measure | occurrence 1 | REQ_MCU_003

#### DFC_DRV_02 Motor stall without plunger advance

* Failure mode: Motor stalls and the plunger does not advance
* Cause: Loss of step torque from winding degradation or gear train wear
* Hazard: Underdelivery of insulin
* Hazardous situation: Programmed basal insulin is not delivered for several hours and no alarm is raised
* Harm: Hyperglycemia progressing to diabetic ketoacidosis
* Detection before controls: User observation
* Occurrence before controls: Occasional
* Risk control: RCM_DRV_02 | Encoder based stall detection with a no delivery alarm | protective measure | occurrence 2, detectability 3 | REQ_DRV_002

### 3.2 Lead Screw and Plunger Coupling (CMP_DRV_02)

A stainless steel lead screw translates gear train rotation into linear motion of the drive nut. The plunger coupling latches the drive nut to the reservoir plunger rod so that the plunger can only move when the motor turns. The coupling is the only mechanical barrier against free flow when the pump is carried above the infusion site.

**Requirements**

* **REQ_DRV_003** The plunger coupling shall withstand an axial separation force of at least 25 newtons after 10000 engagement cycles. [Verified by: VER_DRV_003] [Standards: ISO 13485 cl 7.3.3]
* **REQ_DRV_004** Delivered volume shall remain within 5 percent of the programmed volume over the service life at basal rates down to 0.05 units per hour, using encoder feedback to correct plunger position. [Verified by: VER_DRV_004] [Standards: ISO 13485 cl 7.3.3]

**Design failure considerations**

#### DFC_DRV_03 Plunger coupling disengagement and free flow

* Failure mode: Plunger coupling disengages from the lead screw drive nut
* Cause: Wear or fracture of the coupling latch
* Hazard: Overdelivery of insulin
* Hazardous situation: Reservoir contents siphon into the patient when the pump is held above the infusion site
* Harm: Severe hypoglycemia with loss of consciousness
* Detection before controls: No detection
* Occurrence before controls: Remote
* Risk control: RCM_DRV_03 | Positive locking plunger coupling with retention force margin | inherent safety by design | occurrence 1 | REQ_DRV_003

#### DFC_DRV_04 Lead screw backlash and dose inaccuracy

* Failure mode: Lead screw backlash causes inaccurate delivery of small basal increments
* Cause: Thread wear beyond tolerance over the service life
* Hazard: Underdelivery of insulin
* Hazardous situation: Delivered basal volume deviates from the programmed volume over an extended period
* Harm: Transient hyperglycemia correctable by the user
* Detection before controls: User observation
* Occurrence before controls: Occasional
* Risk control: RCM_DRV_04 | Closed loop plunger position correction using encoder feedback | protective measure | occurrence 2 | REQ_DRV_004

## 4 Sensing Subsystem

The sensing subsystem measures plunger load and motor rotation.

### 4.1 Occlusion Force Sensor (CMP_SNS_01)

A strain gauge load cell behind the lead screw thrust bearing measures the axial force needed to advance the plunger. Rising force indicates a blocked infusion line or cannula. The delivery control software samples the sensor before and after every delivery pulse and compares the reading with the occlusion threshold.

**Requirements**

* **REQ_SNS_001** The pump shall perform a force sensor plausibility self test at power on and every 24 hours and shall raise a system error alarm when the test fails. [Verified by: VER_SNS_001] [Standards: IEC 60601 1 cl 4.2]
* **REQ_SNS_002** The pump shall infer occlusion from the motor current signature independently of the force sensor and raise an occlusion alarm when either method detects a blockage. [Verified by: VER_SNS_002] [Standards: IEC 60601 1 8 cl 6.1]
* **REQ_SNS_003** The pump shall raise an occlusion alarm before 3 units of insulin are stored in the line and shall retract the plunger to relieve line pressure when the alarm is raised. [Verified by: VER_SNS_003] [Standards: IEC 60601 1 8 cl 6.1]

**Design failure considerations**

#### DFC_SNS_01 Undetected downstream occlusion

* Failure mode: Force sensor reads low and fails to detect a downstream occlusion
* Cause: Strain gauge drift or delamination of the load cell
* Hazard: Underdelivery of insulin
* Hazardous situation: The infusion line is blocked and insulin is not delivered while no occlusion alarm sounds
* Harm: Hyperglycemia progressing to diabetic ketoacidosis
* Detection before controls: No detection
* Occurrence before controls: Occasional
* Risk control: RCM_SNS_01 | Force sensor plausibility self test at power on and every 24 hours | protective measure | detectability 2 | REQ_SNS_001
* Risk control: RCM_SNS_02 | Redundant occlusion inference from the motor current signature | protective measure | occurrence 2, detectability 1 | REQ_SNS_002

#### DFC_SNS_02 Unintended bolus on release of an occlusion

* Failure mode: Occlusion clears suddenly and releases insulin accumulated in the line
* Cause: Pressure stored behind a kinked cannula is released when the kink straightens
* Hazard: Overdelivery of insulin
* Hazardous situation: Stored insulin is delivered as an unintended bolus when the occlusion releases
* Harm: Moderate hypoglycemia requiring assistance
* Detection before controls: User observation
* Occurrence before controls: Occasional
* Risk control: RCM_SNS_03 | Occlusion alarm threshold that limits stored volume, with plunger retraction on alarm | protective measure | occurrence 2 | REQ_SNS_003
* Risk control: RCM_IFU_01 | Instructions directing the user to disconnect before clearing an occlusion | information for safety | occurrence 1 | REQ_LBL_001

#### DFC_SNS_03 False occlusion alarms

* Failure mode: Force sensor noise triggers occlusion alarms when no occlusion is present
* Cause: Mechanical vibration and temperature change shift the force baseline
* Hazard: Loss of therapy
* Hazardous situation: Delivery stops repeatedly for false occlusion alarms and the user delays restarting delivery
* Harm: Transient hyperglycemia correctable by the user
* Detection before controls: Continuous monitoring with alarm
* Occurrence before controls: Probable
* Risk control: none defined at this revision

### 4.2 Motor Rotary Encoder (CMP_SNS_02)

An optical quadrature encoder on the motor shaft reports actual rotation to both the main controller and the safety supervisor. Encoder counts close the delivery control loop and give the supervisor an independent measure of delivered volume.

**Requirements**

* **REQ_SNS_004** The safety supervisor shall cross check encoder counts against commanded steps and motor current on every delivery pulse and shall stop delivery when they disagree. [Verified by: VER_SNS_004] [Standards: IEC 62304 cl 7.2]

**Design failure considerations**

#### DFC_SNS_04 Encoder undercount

* Failure mode: Encoder undercounts motor rotation
* Cause: Contamination of the optical encoder disc
* Hazard: Overdelivery of insulin
* Hazardous situation: The controller commands extra motor steps to compensate and delivers more insulin than programmed
* Harm: Severe hypoglycemia with loss of consciousness
* Detection before controls: No detection
* Occurrence before controls: Remote
* Risk control: RCM_SNS_05 | Supervisor cross check of encoder counts against commanded steps and motor current | protective measure | occurrence 1, detectability 3 | REQ_SNS_004

## 5 Fluid Path

The fluid path carries insulin from the reservoir to the subcutaneous tissue.

### 5.1 Insulin Reservoir and Seal (CMP_RSV_01)

The single use 3 milliliter reservoir is a cyclic olefin barrel with an elastomer plunger and O ring seal. It is supplied sterile in a sealed pouch and is filled by the user from a vial. The reservoir compartment is closed by a threaded cap that also retains the infusion set connector.

**Requirements**

* **REQ_RSV_001** The reservoir seal shall remain leak tight at 150 kilopascals over the labeled single use period of three days. [Verified by: VER_RSV_001] [Standards: ISO 13485 cl 7.3.3]
* **REQ_RSV_002** The pump shall guide the user through a priming sequence and require confirmation that fluid is visible at the cannula tip before delivery can start. [Verified by: VER_RSV_002] [Standards: IEC 62366 1 cl 5.4]
* **REQ_RSV_003** The reservoir shall be supplied in a validated sterile barrier package that carries a visible integrity indicator. [Verified by: VER_RSV_003] [Standards: ISO 13485 cl 7.3.3]

**Design failure considerations**

#### DFC_RSV_01 Reservoir seal leak

* Failure mode: Reservoir seal leaks insulin into the reservoir compartment
* Cause: O ring compression set or a cracked reservoir barrel
* Hazard: Underdelivery of insulin
* Hazardous situation: Insulin leaks into the pump instead of reaching the patient while the dose counter still records delivery
* Harm: Hyperglycemia progressing to diabetic ketoacidosis
* Detection before controls: User observation
* Occurrence before controls: Occasional
* Risk control: RCM_RSV_01 | Validated seal compression design with a single use reservoir limit | inherent safety by design | occurrence 2 | REQ_RSV_001
* Risk control: RCM_IFU_02 | Instructions to inspect the reservoir compartment at every reservoir change | information for safety | detectability 1 | REQ_LBL_002

#### DFC_RSV_02 Air bubbles in the reservoir

* Failure mode: Air bubbles in the reservoir are delivered in place of insulin
* Cause: Incomplete priming or outgassing of cold insulin as it warms
* Hazard: Underdelivery of insulin
* Hazardous situation: Air displaces insulin in the infusion line during basal delivery
* Harm: Transient hyperglycemia correctable by the user
* Detection before controls: User observation
* Occurrence before controls: Probable
* Risk control: RCM_RSV_02 | Guided priming sequence with user confirmation of fluid at the cannula tip | protective measure | occurrence 1 | REQ_RSV_002
* Risk control: RCM_IFU_03 | Illustrated instructions on priming and removal of air bubbles | information for safety | occurrence 1 | REQ_LBL_003

#### DFC_RSV_03 Loss of sterility of the fluid path

* Failure mode: Sterile barrier of the reservoir package is breached before use
* Cause: Pouch seal damage during distribution
* Hazard: Biological contamination
* Hazardous situation: A contaminated fluid path is connected to the subcutaneous tissue
* Harm: Infusion site infection
* Detection before controls: No detection
* Occurrence before controls: Remote
* Risk control: RCM_RSV_03 | Validated sterile barrier packaging with integrity indicator | inherent safety by design | occurrence 1, detectability 2 | REQ_RSV_003

### 5.2 Infusion Set Connector (CMP_INF_01)

The infusion set connector joins the reservoir outlet to the tubing that leads to the subcutaneous cannula. The connector is keyed so that only compatible infusion sets can be attached and it locks with a quarter turn.

**Requirements**

* **REQ_INF_001** The infusion set connector shall be keyed and shall give audible and tactile confirmation when fully locked. [Verified by: VER_INF_001] [Standards: IEC 62366 1 cl 5.2]

**Design failure considerations**

#### DFC_INF_01 Infusion set connector detachment

* Failure mode: Infusion set connector detaches from the reservoir
* Cause: Incomplete latch engagement or connector thread wear
* Hazard: Underdelivery of insulin
* Hazardous situation: Insulin is pumped onto skin or clothing instead of into the tissue and no alarm is raised
* Harm: Hyperglycemia progressing to diabetic ketoacidosis
* Detection before controls: User observation
* Occurrence before controls: Occasional
* Risk control: RCM_INF_01 | Keyed connector with audible and tactile lock confirmation | inherent safety by design | occurrence 1 | REQ_INF_001
* Risk control: RCM_IFU_04 | Training on infusion site checks and routine glucose monitoring | information for safety | occurrence 1 | REQ_LBL_004

## 6 Power Subsystem

The power subsystem stores energy, estimates remaining capacity and charges the battery.

### 6.1 Lithium Battery Pack (CMP_PWR_01)

A single cell lithium polymer pack of 500 milliampere hours powers the pump for at least seven days of typical use. The pack contains its own protection circuit and a thermistor that is read by the fuel gauge.

**Requirements**

* **REQ_PWR_001** The battery pack shall include a protection circuit that disconnects the cell on excess current, excess voltage or a cell temperature above 60 degrees Celsius. [Verified by: VER_PWR_001] [Standards: IEC 60601 1 cl 11.1]
* **REQ_PWR_002** Battery cells shall be sourced from a certified supplier and each lot shall pass incoming inspection with lot traceability retained. [Verified by: VER_PWR_002] [Standards: ISO 13485 cl 7.3.3]

**Design failure considerations**

#### DFC_PWR_01 Battery thermal runaway

* Failure mode: Battery cell enters thermal runaway
* Cause: Internal short circuit from a manufacturing defect or mechanical damage
* Hazard: Thermal energy
* Hazardous situation: The pump surface temperature rises rapidly while the pump is worn against the body
* Harm: Skin burn
* Detection before controls: No detection
* Occurrence before controls: Remote
* Risk control: RCM_PWR_01 | Cell protection circuit with current, voltage and temperature cutoff | protective measure | occurrence 1 | REQ_PWR_001
* Risk control: RCM_PWR_02 | Certified cells with incoming inspection and lot traceability | inherent safety by design | occurrence 1 | REQ_PWR_002

#### DFC_PWR_02 Battery depletion without warning

* Failure mode: Battery depletes suddenly without a low battery warning
* Cause: Abrupt capacity loss of an aged cell or at low temperature
* Hazard: Loss of therapy
* Hazardous situation: The pump shuts down during sleep and basal delivery stops for several hours
* Harm: Hyperglycemia progressing to diabetic ketoacidosis
* Detection before controls: No detection
* Occurrence before controls: Occasional
* Risk control: RCM_PWR_03 | Staged low battery alarms with reserved alarm capacity | protective measure | occurrence 1, detectability 3 | REQ_PWR_003
* Risk control: RCM_PWR_04 | Temperature compensated capacity estimation | inherent safety by design | occurrence 1 | REQ_PWR_004

### 6.2 Battery Fuel Gauge (CMP_PWR_02)

The fuel gauge integrates battery current to estimate remaining capacity and reports state of charge to the main controller. Low battery alarms and the decision to stop delivery in an orderly way depend on this estimate.

**Requirements**

* **REQ_PWR_003** The pump shall raise a low battery alarm at 20 percent and a critical battery alarm at 5 percent remaining capacity and shall reserve capacity for at least 30 minutes of alarm annunciation. [Verified by: VER_PWR_003] [Standards: IEC 60601 1 8 cl 6.1]
* **REQ_PWR_004** The fuel gauge shall compensate capacity estimates for cell temperature between 5 and 40 degrees Celsius. [Verified by: VER_PWR_004] [Standards: ISO 13485 cl 7.3.3]
* **REQ_PWR_005** The pump shall raise the critical battery alarm when cell voltage falls below 3.3 volts regardless of the coulomb counter estimate. [Verified by: VER_PWR_005] [Standards: IEC 60601 1 cl 4.2]
* **REQ_PWR_006** The battery shall charge from empty to full in no more than two hours. [Verified by: VER_PWR_006]

**Design failure considerations**

#### DFC_PWR_03 Fuel gauge overestimation

* Failure mode: Fuel gauge overestimates the remaining battery capacity
* Cause: Coulomb counter drift without recalibration
* Hazard: Loss of therapy
* Hazardous situation: The displayed battery level stays normal until the pump shuts down abruptly
* Harm: Hyperglycemia progressing to diabetic ketoacidosis
* Detection before controls: No detection
* Occurrence before controls: Occasional
* Risk control: RCM_PWR_05 | Voltage based critical battery threshold independent of the coulomb counter | protective measure | occurrence 2, detectability 1 | REQ_PWR_005

### 6.3 Charging Circuit (CMP_CHG_01)

The pump is charged from a USB power source through a magnetic charging port. Users may charge the pump while wearing it, so the charging path is a potential route from mains voltage to the patient.

**Requirements**

* **REQ_CHG_001** The charging path shall provide reinforced isolation between the charging port and all patient accessible parts. [Verified by: VER_CHG_001] [Standards: IEC 60601 1 cl 8.5]

**Design failure considerations**

#### DFC_CHG_01 Charger isolation failure

* Failure mode: Isolation between the charging port and patient accessible parts fails
* Cause: Use of a damaged or counterfeit USB power source while the pump is worn
* Hazard: Electrical energy
* Hazardous situation: Mains voltage reaches the enclosure while the pump is connected to the patient
* Harm: Electric shock
* Detection before controls: No detection
* Occurrence before controls: Remote
* Risk control: RCM_CHG_01 | Reinforced isolation between the charging port and patient accessible parts | inherent safety by design | occurrence 1 | REQ_CHG_001

## 7 Alarm Hardware, Enclosure and Accessories

This section covers the annunciators, the housing and the wearable accessories.

### 7.1 Audible and Vibratory Alarm Hardware (CMP_ALM_01)

A piezoelectric speaker and an eccentric mass vibration motor annunciate alarms raised by the alarm manager software. Both are driven from a supply rail that remains powered by reserved battery capacity after delivery has stopped.

**Requirements**

* **REQ_ALM_001** The pump shall test the speaker by current sensing at power on and before each alarm and shall annunciate by vibration and display when the speaker test fails. [Verified by: VER_ALM_001] [Standards: IEC 60601 1 8 cl 6.3]
* **REQ_ALM_002** Unacknowledged high priority alarms shall escalate to maximum volume with repeated vibration until acknowledged. [Verified by: VER_ALM_002] [Standards: IEC 60601 1 8 cl 6.3]

**Design failure considerations**

#### DFC_ALM_01 Speaker failure

* Failure mode: Speaker fails and the audible alarm is silent
* Cause: Open circuit of the speaker element or a blocked sound port
* Hazard: Loss of alarm information
* Hazardous situation: An occlusion or low battery alarm is shown on the display but is not heard during sleep
* Harm: Hyperglycemia progressing to diabetic ketoacidosis
* Detection before controls: No detection
* Occurrence before controls: Occasional
* Risk control: RCM_ALM_01 | Speaker self test by current sensing with redundant vibration annunciation | protective measure | occurrence 2, detectability 2 | REQ_ALM_001

#### DFC_ALM_02 Alarm not perceived

* Failure mode: Alarm volume is insufficient for the user to perceive the alarm
* Cause: Low volume setting or the pump is muffled under clothing and bedding
* Hazard: Loss of alarm information
* Hazardous situation: A no delivery alarm sounds but is not heard and delivery remains stopped
* Harm: Sustained hyperglycemia requiring medical intervention
* Detection before controls: User observation
* Occurrence before controls: Probable
* Risk control: RCM_ALM_02 | Escalating alarm volume with repeated vibration until acknowledged | protective measure | occurrence 2 | REQ_ALM_002

### 7.2 Enclosure and Ingress Protection (CMP_ENC_01)

The polycarbonate enclosure houses all electronics and the drive train. A perimeter gasket and sealed charging contacts provide protection against immersion. The enclosure is in continuous contact with the skin or clothing of the user.

**Requirements**

* **REQ_ENC_001** The enclosure shall meet IPX8 at 2.4 meters for 60 minutes after a one meter drop on each face. [Verified by: VER_ENC_001] [Standards: IEC 60601 1 cl 11.6]
* **REQ_ENC_002** The pump shall detect moisture inside the electronics compartment, raise a system error alarm and stop delivery. [Verified by: VER_ENC_002] [Standards: IEC 60601 1 cl 4.2]
* **REQ_ENC_003** The enclosure shall be made of impact resistant polymer with all external edges rounded to a radius of at least 0.5 millimeters. [Verified by: VER_ENC_003] [Standards: IEC 60601 1 cl 9.3; IEC 60601 1 cl 15.3]

**Design failure considerations**

#### DFC_ENC_01 Water ingress

* Failure mode: Water enters the electronics compartment
* Cause: Gasket damage after a drop or gasket ageing
* Hazard: Loss of therapy
* Hazardous situation: Moisture short circuits the electronics and the pump stops delivery without a valid alarm
* Harm: Hyperglycemia progressing to diabetic ketoacidosis
* Detection before controls: No detection
* Occurrence before controls: Occasional
* Risk control: RCM_ENC_01 | IPX8 sealed enclosure with drop tested gasket retention | inherent safety by design | occurrence 2 | REQ_ENC_001
* Risk control: RCM_ENC_02 | Moisture sensor that triggers an alarm and a transition to the safe state | protective measure | detectability 2 | REQ_ENC_002

#### DFC_ENC_02 Cracked enclosure

* Failure mode: Enclosure cracks and exposes a sharp edge
* Cause: Impact damage from a drop onto a hard surface
* Hazard: Mechanical contact
* Hazardous situation: A sharp edge of the cracked case rubs against the skin during wear
* Harm: Minor skin laceration
* Detection before controls: User observation
* Occurrence before controls: Remote
* Risk control: RCM_ENC_03 | Impact resistant polymer housing with rounded edge geometry | inherent safety by design | occurrence 1 | REQ_ENC_003

### 7.3 Belt Clip and Holster (CMP_ACC_01)

A detachable belt clip and a fabric holster allow the pump to be worn on a waistband. The accessory carries no electronics and has no direct role in insulin delivery. No design failure considerations have been recorded for this component at the current revision.

