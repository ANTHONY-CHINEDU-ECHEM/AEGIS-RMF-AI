# Usability and Connectivity Specification

* Document ID: UCS_004
* Revision: C
* Device: Aurelia P200 Ambulatory Insulin Infusion Pump
* Status: Released for design verification
* Related documents: SAS_001, VVR_005, RMP_006

This document describes a fictional device created for the Aegis RMF AI project. It is not derived from any commercial product.

## 1 Purpose

This specification defines the user interface, the wireless interfaces and the labeling of the Aurelia P200, together with the hazard related use scenarios identified under IEC 62366 1 cl 5.4.

## 2 Users, use environments and conventions

Intended users are patients aged six years and older and their caregivers. Users may have reduced visual acuity, reduced dexterity or impaired awareness of low glucose. The pump is used in homes, schools, workplaces, vehicles and outdoors, in darkness and in bright sunlight, and in noisy settings. Requirements carry the identifier prefix REQ and are verified by the records listed in VVR_005. Design failure considerations carry the prefix DFC and record, for each foreseeable failure of a component, the failure mode, its cause, the hazard, the hazardous situation, the harm, the means of detection and the estimated occurrence before risk controls, followed by the risk control measures that address it. Each risk control line lists the control identifier, its description, its type under ISO 14971 cl 7.1, the claimed reduction in rating levels and the requirements that implement it.

## 3 User Interface

The user interface is the route for most use errors that affect dosing.

### 3.1 Touchscreen and Keypad (CMP_UI_01)

A color touchscreen and three physical keys form the primary user interface. Users program basal profiles, request boluses and acknowledge alarms through this interface, often in poor lighting or while distracted.

**Requirements**

* **REQ_UI_001** The screen shall lock after 30 seconds of inactivity, shall require an unlock gesture and shall require two separate confirmations before a bolus starts. [Verified by: VER_UI_001] [Standards: IEC 62366 1 cl 5.4]
* **REQ_UI_002** Dose entry shall use a fixed decimal format and shall display a large dose warning when the entry exceeds twice the average bolus of the user. [Verified by: VER_UI_002] [Standards: IEC 62366 1 cl 5.4; IEC 62366 1 cl 5.9]
* **REQ_UI_003** Each alarm priority shall have a distinct audible pattern that identifies the priority without reference to the display. [Verified by: VER_UI_003] [Standards: IEC 60601 1 8 cl 6.3]
* **REQ_UI_004** The user interface shall be available in English, Spanish, French and German. [Verified by: VER_UI_004]

**Design failure considerations**

#### DFC_UI_01 Unintended bolus from accidental touch

* Failure mode: Unintended touch or key activation starts a bolus
* Cause: Pressure on the touchscreen in a pocket or during sleep
* Hazard: Overdelivery of insulin
* Hazardous situation: A bolus is started without the intent of the user
* Harm: Severe hypoglycemia with loss of consciousness
* Detection before controls: No detection
* Occurrence before controls: Occasional
* Risk control: RCM_UI_01 | Automatic screen lock with unlock gesture and two step bolus confirmation | inherent safety by design | occurrence 2 | REQ_UI_001

#### DFC_UI_02 Decimal dose entry error

* Failure mode: User enters a bolus dose with a misplaced decimal point
* Cause: Ambiguous numeric entry format leads to a tenfold use error
* Hazard: Use error
* Hazardous situation: A bolus ten times larger than intended is confirmed and delivered
* Harm: Severe hypoglycemia with loss of consciousness
* Detection before controls: User observation
* Occurrence before controls: Occasional
* Risk control: RCM_UI_02 | Fixed decimal dose entry with maximum bolus limit and large dose warning | inherent safety by design | occurrence 2 | REQ_UI_002, REQ_SW_001
* Risk control: RCM_IFU_05 | Training module on bolus entry with knowledge check | information for safety | occurrence 1 | REQ_LBL_005

#### DFC_UI_03 Display unreadable

* Failure mode: Display fails or becomes unreadable
* Cause: Backlight failure or a cracked display panel
* Hazard: Loss of alarm information
* Hazardous situation: The user cannot read alarm text or verify bolus entries
* Harm: Sustained hyperglycemia requiring medical intervention
* Detection before controls: User observation
* Occurrence before controls: Occasional
* Risk control: RCM_UI_03 | Distinct audible alarm patterns per priority that allow response without the display | protective measure | occurrence 1 | REQ_UI_003

## 4 Connectivity

Wireless interfaces extend the attack surface of the pump and introduce dependence on data that may be late or wrong.

### 4.1 Bluetooth Communication Module (CMP_COM_01)

A Bluetooth low energy radio links the pump with the companion phone application and with the continuous glucose sensor transmitter. The companion application can display status, change settings and request a remote bolus.

Software safety class under IEC 62304 cl 4.3: Class C.

**Requirements**

* **REQ_COM_001** Pairing shall use authenticated encrypted connections with keys generated per session. [Verified by: VER_COM_001] [Standards: IEC 62304 cl 7.2]
* **REQ_COM_002** A bolus requested from the companion application shall be delivered only after confirmation on the pump. [Verified by: VER_COM_002] [Standards: IEC 62304 cl 7.2; IEC 62366 1 cl 5.4]
* **REQ_COM_003** The pump shall display the age of the latest glucose value and the bolus calculator shall refuse glucose values older than 15 minutes. [Verified by: VER_COM_003] [Standards: IEC 62304 cl 7.2]
* **REQ_COM_004** Every remote setting change shall carry a message authentication code and shall pass range validation before it is applied. [Verified by: VER_COM_004] [Standards: IEC 62304 cl 7.2]
* **REQ_COM_005** The pump shall export delivery history to the companion application on request. [Verified by: VER_COM_005]

**Design failure considerations**

#### DFC_COM_01 Unauthorized remote bolus command

* Failure mode: Unauthorized remote bolus command is accepted
* Cause: Weak pairing authentication is exploited by an attacker within radio range
* Hazard: Cybersecurity compromise
* Hazardous situation: A third party triggers insulin delivery without the knowledge of the user
* Harm: Severe hypoglycemia with loss of consciousness
* Detection before controls: No detection
* Occurrence before controls: Remote
* Risk control: RCM_COM_01 | Authenticated encrypted pairing with keys generated per session | inherent safety by design | occurrence 1 | REQ_COM_001
* Risk control: RCM_COM_02 | Remote bolus requires confirmation on the pump | protective measure | occurrence 1, detectability 2 | REQ_COM_002

#### DFC_COM_02 Stale glucose data after connection loss

* Failure mode: Connection to the glucose sensor is lost and glucose values stop updating
* Cause: Radio interference or the transmitter is out of range
* Hazard: Loss of alarm information
* Hazardous situation: The user doses on a stale glucose value that no longer reflects the current level
* Harm: Moderate hypoglycemia requiring assistance
* Detection before controls: User observation
* Occurrence before controls: Probable
* Risk control: RCM_COM_03 | Stale data indicator with rejection of glucose values older than 15 minutes | protective measure | occurrence 2, detectability 2 | REQ_COM_003

#### DFC_COM_03 Corrupted setting change accepted

* Failure mode: Corrupted data packet is accepted as a valid setting change
* Cause: Insufficient message integrity checking
* Hazard: Incorrect therapy settings
* Hazardous situation: The basal profile is updated with corrupted values
* Harm: Severe hypoglycemia with loss of consciousness
* Detection before controls: No detection
* Occurrence before controls: Remote
* Risk control: RCM_COM_04 | Message authentication code with range validation on all remote setting changes | inherent safety by design | occurrence 1 | REQ_COM_004

### 4.2 Glucose Sensor Data Interface (CMP_CGM_01)

The glucose sensor data interface receives interstitial glucose values every five minutes. The values feed the bolus calculator and the automated correction feature that adjusts delivery toward the target glucose.

Software safety class under IEC 62304 cl 4.3: Class C.

**Requirements**

* **REQ_CGM_001** Glucose values shall pass a rate of change plausibility filter and any automated correction shall be capped at the configured maximum correction dose. [Verified by: VER_CGM_001] [Standards: IEC 62304 cl 7.2]

**Design failure considerations**

#### DFC_CGM_01 False high glucose drives automated correction

* Failure mode: Falsely high glucose reading is used for automated correction
* Cause: Sensor compression artifact or calibration error passes without a plausibility check
* Hazard: Overdelivery of insulin
* Hazardous situation: Automated correction delivers insulin against a false high reading
* Harm: Severe hypoglycemia with loss of consciousness
* Detection before controls: No detection
* Occurrence before controls: Occasional
* Risk control: RCM_CGM_01 | Rate of change plausibility filter with a cap on automated correction doses | protective measure | occurrence 2 | REQ_CGM_001
* Risk control: RCM_IFU_06 | Labeling that instructs fingerstick confirmation before large corrections | information for safety | occurrence 1 | REQ_LBL_006

## 5 Labeling and Training

Labeling and training are information for safety and are the lowest priority form of risk control.

### 5.1 Labeling and Instructions for Use (CMP_LBL_01)

Labeling comprises the instructions for use, the quick reference guide, on screen help and the structured training programme delivered by certified trainers before first use.

**Requirements**

* **REQ_LBL_001** The instructions for use shall direct the user to disconnect the infusion set from the body before clearing an occlusion. [Verified by: VER_LBL_001] [Standards: IEC 62366 1 cl 5.9]
* **REQ_LBL_002** The instructions for use shall direct the user to inspect the reservoir compartment for moisture at every reservoir change. [Standards: IEC 62366 1 cl 5.9]
* **REQ_LBL_003** The instructions for use shall describe priming and removal of air bubbles with illustrations. [Verified by: VER_LBL_003] [Standards: IEC 62366 1 cl 5.9]
* **REQ_LBL_004** Training shall cover infusion site checks and routine glucose monitoring, including the response to unexplained high glucose. [Verified by: VER_LBL_004] [Standards: IEC 62366 1 cl 5.9]
* **REQ_LBL_005** Training shall include a bolus entry module that ends with a knowledge check. [Verified by: VER_LBL_005] [Standards: IEC 62366 1 cl 5.9]
* **REQ_LBL_006** Labeling shall instruct the user to confirm glucose with a fingerstick measurement before accepting a large correction. [Verified by: VER_LBL_006] [Standards: IEC 62366 1 cl 5.9]
* **REQ_LBL_007** The pump shall remind the user to change the infusion site at a configurable interval of two or three days. [Verified by: VER_LBL_007] [Standards: IEC 62366 1 cl 5.4]
* **REQ_LBL_008** Instructions on the infusion set change interval shall be validated for comprehension in the summative usability evaluation. [Verified by: VER_LBL_008] [Standards: IEC 62366 1 cl 5.9; ISO 13485 cl 7.3.7]

**Design failure considerations**

#### DFC_LBL_01 Infusion set worn beyond the change interval

* Failure mode: Instructions on the infusion set change interval are misunderstood
* Cause: Ambiguous wording and low readability of the instructions
* Hazard: Use error
* Hazardous situation: The infusion set is worn beyond the recommended interval
* Harm: Infusion site infection
* Detection before controls: User observation
* Occurrence before controls: Probable
* Risk control: RCM_LBL_01 | Infusion site change reminder with configurable interval | protective measure | occurrence 2 | REQ_LBL_007
* Risk control: RCM_LBL_02 | Instructions on set change interval validated for comprehension | information for safety | occurrence 1 | REQ_LBL_008

