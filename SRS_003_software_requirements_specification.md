# Software Requirements Specification

* Document ID: SRS_003
* Revision: F
* Device: Aurelia P200 Ambulatory Insulin Infusion Pump
* Status: Released for design verification
* Related documents: SAS_001, VVR_005, RMP_006

This document describes a fictional device created for the Aegis RMF AI project. It is not derived from any commercial product.

## 1 Purpose

This specification defines the software items of the Aurelia P200, their requirements and the software causes of hazardous situations identified under IEC 62304 cl 7.1.

## 2 Conventions and safety classification

Requirements carry the identifier prefix REQ and are verified by the records listed in VVR_005. Design failure considerations carry the prefix DFC and record, for each foreseeable failure of a component, the failure mode, its cause, the hazard, the hazardous situation, the harm, the means of detection and the estimated occurrence before risk controls, followed by the risk control measures that address it. Each risk control line lists the control identifier, its description, its type under ISO 14971 cl 7.1, the claimed reduction in rating levels and the requirements that implement it. All therapy software items are Class C because a failure could contribute to death or serious injury. The real time clock service is Class B.

## 3 Platform and Supervision

The platform hosts the therapy applications and the supervisor constrains them.

### 3.1 Main Controller Firmware Platform (CMP_MCU_01)

The main controller runs the real time operating system, device drivers and all therapy applications. It owns the delivery schedule, user interface and communication stack. Platform services include task scheduling, memory protection and the hardware watchdog service.

Software safety class under IEC 62304 cl 4.3: Class C.

**Requirements**

* **REQ_MCU_001** A hardware watchdog shall reset the main controller when it is not serviced for 500 milliseconds and the safety supervisor shall raise a system error alarm after any watchdog reset. [Verified by: VER_MCU_001] [Standards: IEC 62304 cl 7.2]
* **REQ_MCU_002** Delivery rate, bolus amount and delivery totals shall be stored in triplicate with majority voting and range checking before each delivery pulse. [Verified by: VER_MCU_002] [Standards: IEC 62304 cl 7.2]

**Design failure considerations**

#### DFC_MCU_01 Firmware hang during delivery

* Failure mode: Main controller firmware hangs during delivery
* Cause: Software deadlock or stack overflow
* Hazard: Loss of therapy
* Hazardous situation: Delivery halts and the display freezes while no alarm is raised
* Harm: Hyperglycemia progressing to diabetic ketoacidosis
* Detection before controls: No detection
* Occurrence before controls: Occasional
* Risk control: RCM_MCU_01 | Hardware watchdog reset with system error alarm from the safety supervisor | protective measure | occurrence 2, detectability 3 | REQ_MCU_001

#### DFC_MCU_02 Corruption of the active delivery rate

* Failure mode: Memory corruption alters the active delivery rate variable
* Cause: Stray pointer write or radiation induced bit flip
* Hazard: Overdelivery of insulin
* Hazardous situation: The pump delivers at a rate many times higher than programmed
* Harm: Severe hypoglycemia with loss of consciousness
* Detection before controls: No detection
* Occurrence before controls: Remote
* Risk control: RCM_MCU_02 | Critical variables stored in triplicate with voting and range check before each delivery | inherent safety by design | occurrence 1 | REQ_MCU_002
* Risk control: RCM_MCU_03 | Independent hourly delivery limit enforced by the safety supervisor | protective measure | occurrence 1 | REQ_MCU_003

### 3.2 Safety Supervisor Processor (CMP_MCU_02)

The safety supervisor is a separate low power processor with its own oscillator and firmware. It monitors encoder counts, delivery totals and the heartbeat of the main controller, and it alone controls the motor power switch. The supervisor is the principal independent protective measure against overdelivery.

Software safety class under IEC 62304 cl 4.3: Class C.

**Requirements**

* **REQ_MCU_003** The safety supervisor shall independently limit total delivery to the configured hourly maximum and shall remove motor power when the limit is reached. [Verified by: VER_MCU_003] [Standards: IEC 62304 cl 7.2; IEC 60601 1 cl 4.2]
* **REQ_MCU_004** The main controller and the safety supervisor shall exchange heartbeat messages every second and either processor shall raise a system error alarm within three seconds of losing the heartbeat of the other. [Verified by: VER_MCU_004] [Standards: IEC 62304 cl 7.2]

**Design failure considerations**

#### DFC_MCU_03 Silent failure of the safety supervisor

* Failure mode: Safety supervisor stops monitoring and the failure remains latent
* Cause: Supervisor oscillator failure or supervisor firmware fault
* Hazard: Overdelivery of insulin
* Hazardous situation: A later drive fault is not intercepted because the independent monitor is inactive
* Harm: Severe hypoglycemia with loss of consciousness
* Detection before controls: No detection
* Occurrence before controls: Improbable
* Risk control: RCM_MCU_04 | Mutual heartbeat between main controller and safety supervisor with alarm on loss | protective measure | detectability 3 | REQ_MCU_004

## 4 Therapy Applications

The therapy applications calculate, schedule and deliver insulin and manage alarms.

### 4.1 Dose Calculation Software (CMP_SW_01)

The dose calculation software implements the bolus calculator. It combines the current glucose value, carbohydrate entry, insulin to carbohydrate ratio, correction factor, target glucose and insulin on board to recommend a bolus that the user may accept or change.

Software safety class under IEC 62304 cl 4.3: Class C.

**Requirements**

* **REQ_SW_001** The pump shall reject any bolus above the configured maximum bolus limit. [Verified by: VER_SW_001] [Standards: IEC 62304 cl 7.2]
* **REQ_SW_002** The bolus confirmation screen shall display the glucose value, carbohydrate entry and insulin on board used in the calculation before the user can confirm. [Verified by: VER_SW_002] [Standards: IEC 62304 cl 5.2; IEC 62366 1 cl 5.4]
* **REQ_SW_003** The glucose unit shall be selected once during setup and locked, and glucose entries outside the valid range for that unit shall be rejected. [Verified by: VER_SW_003] [Standards: IEC 62304 cl 7.2]
* **REQ_SW_004** Insulin on board shall be stored with an integrity check and displayed on the bolus screen. [Verified by: VER_SW_004] [Standards: IEC 62304 cl 7.2]
* **REQ_SW_005** Insulin on board and the active insulin time shall be retained without change across clock changes, battery changes and software updates. [Verified by: VER_SW_005] [Standards: IEC 62304 cl 7.2; IEC 62304 cl 7.4]

**Design failure considerations**

#### DFC_SW_01 Excessive bolus recommendation

* Failure mode: Bolus calculator recommends an excessive dose
* Cause: Unit conversion defect between glucose units in the correction calculation
* Hazard: Overdelivery of insulin
* Hazardous situation: The user accepts a recommended bolus several times larger than needed
* Harm: Severe hypoglycemia with loss of consciousness
* Detection before controls: User observation
* Occurrence before controls: Occasional
* Risk control: RCM_SW_01 | Maximum bolus limit and confirmation screen showing the calculation inputs | protective measure | occurrence 1, detectability 1 | REQ_SW_001, REQ_SW_002
* Risk control: RCM_SW_02 | Glucose unit locked at setup with range validation of glucose entries | inherent safety by design | occurrence 2 | REQ_SW_003

#### DFC_SW_02 Insulin on board not subtracted

* Failure mode: Insulin on board is not subtracted from a correction bolus
* Cause: Active insulin time is reset to default after a clock change or software update
* Hazard: Overdelivery of insulin
* Hazardous situation: Repeated correction boluses stack because earlier insulin is ignored
* Harm: Moderate hypoglycemia requiring assistance
* Detection before controls: No detection
* Occurrence before controls: Probable
* Risk control: RCM_SW_03 | Insulin on board persisted with integrity check and shown on the bolus screen | protective measure | occurrence 2 | REQ_SW_004, REQ_SW_005

### 4.2 Delivery Control Software (CMP_SW_02)

The delivery control software converts basal schedules, temporary basal rates and bolus requests into motor commands. It manages the delivery state machine including running, suspended and alarm states.

Software safety class under IEC 62304 cl 4.3: Class C.

**Requirements**

* **REQ_SW_006** Any change to the pump clock of more than 30 minutes shall require user confirmation and shall prompt a review of the active basal schedule. [Verified by: VER_SW_006] [Standards: IEC 62304 cl 7.2]
* **REQ_SW_007** While delivery is suspended the pump shall show a persistent suspended indicator and raise a reminder alarm every 15 minutes. [Verified by: VER_SW_007] [Standards: IEC 60601 1 8 cl 6.1]
* **REQ_SW_008** A user initiated suspension shall end automatically after the selected duration, which shall not exceed two hours. [Verified by: VER_SW_008] [Standards: IEC 62304 cl 7.2]
* **REQ_SW_009** Every bolus command shall carry a unique identifier, shall be executed at most once and shall be followed by a lockout interval before another bolus of the same amount is accepted. [Verified by: VER_SW_009] [Standards: IEC 62304 cl 7.2]

**Design failure considerations**

#### DFC_SW_03 Basal schedule applied to the wrong time segment

* Failure mode: Basal schedule is applied to the wrong time segment
* Cause: Scheduler handles a time zone or clock change incorrectly
* Hazard: Incorrect therapy settings
* Hazardous situation: The overnight basal rate is delivered during the day or the daytime rate overnight
* Harm: Moderate hypoglycemia requiring assistance
* Detection before controls: No detection
* Occurrence before controls: Occasional
* Risk control: RCM_SW_04 | Clock change confirmation with basal schedule review prompt | protective measure | occurrence 2, detectability 1 | REQ_SW_006

#### DFC_SW_04 Suspended delivery does not resume

* Failure mode: Suspended delivery does not resume when expected
* Cause: State machine transition defect after alarm acknowledgment
* Hazard: Underdelivery of insulin
* Hazardous situation: The pump remains suspended after the user believes delivery has resumed
* Harm: Hyperglycemia progressing to diabetic ketoacidosis
* Detection before controls: User observation
* Occurrence before controls: Occasional
* Risk control: RCM_SW_05 | Persistent suspended indicator with periodic reminder alarm | protective measure | occurrence 1, detectability 2 | REQ_SW_007
* Risk control: RCM_SW_06 | Automatic resume timer that bounds the maximum suspension period | inherent safety by design | occurrence 1 | REQ_SW_008

#### DFC_SW_05 Bolus command executed twice

* Failure mode: Bolus command is executed twice
* Cause: Duplicate command processing after a communication retry
* Hazard: Overdelivery of insulin
* Hazardous situation: A single bolus request delivers double the intended dose
* Harm: Moderate hypoglycemia requiring assistance
* Detection before controls: No detection
* Occurrence before controls: Remote
* Risk control: RCM_SW_07 | Unique command identifiers with idempotent execution and a bolus lockout interval | inherent safety by design | occurrence 1 | REQ_SW_009

### 4.3 Alarm Manager Software (CMP_SW_03)

The alarm manager receives alarm conditions from every subsystem, assigns priority and drives the display, speaker and vibration motor. It keeps an alarm log and manages acknowledgment and escalation.

Software safety class under IEC 62304 cl 4.3: Class C.

**Requirements**

* **REQ_SW_010** The alarm manager shall annunciate the highest priority active alarm at all times and shall preempt any lower priority alarm in progress. [Verified by: VER_SW_010] [Standards: IEC 60601 1 8 cl 6.1; IEC 62304 cl 7.2]

**Design failure considerations**

#### DFC_SW_06 High priority alarm suppressed

* Failure mode: High priority alarm is suppressed by lower priority alarms in the queue
* Cause: Priority inversion in alarm queue handling
* Hazard: Loss of alarm information
* Hazardous situation: An occlusion or no delivery condition is not annunciated
* Harm: Hyperglycemia progressing to diabetic ketoacidosis
* Detection before controls: No detection
* Occurrence before controls: Remote
* Risk control: RCM_SW_08 | Preemptive priority based alarm scheduling | inherent safety by design | occurrence 1 | REQ_SW_010

## 5 Platform Services

Platform services store settings and keep time.

### 5.1 Nonvolatile Settings Memory (CMP_MEM_01)

Therapy settings, basal profiles and delivery history are stored in serial flash memory. Settings must survive battery removal and unexpected resets without alteration.

Software safety class under IEC 62304 cl 4.3: Class C.

**Requirements**

* **REQ_MEM_001** Settings shall be written atomically to two copies protected by checksums, and delivery shall be blocked with a system error alarm when no valid copy exists. [Verified by: VER_MEM_001] [Standards: IEC 62304 cl 7.2]

**Design failure considerations**

#### DFC_MEM_01 Therapy settings revert to defaults

* Failure mode: Therapy settings revert to factory defaults
* Cause: Flash write interrupted by power loss
* Hazard: Incorrect therapy settings
* Hazardous situation: The pump resumes delivery with a default basal profile that does not match the prescription
* Harm: Moderate hypoglycemia requiring assistance
* Detection before controls: No detection
* Occurrence before controls: Occasional
* Risk control: RCM_MEM_01 | Atomic settings writes with checksum and dual copies, with delivery blocked when settings are invalid | protective measure | occurrence 2, detectability 2 | REQ_MEM_001

### 5.2 Real Time Clock (CMP_RTC_01)

The real time clock provides the time of day used to select the active basal segment and to stamp history records. It is kept alive during battery changes by a backup capacitor.

Software safety class under IEC 62304 cl 4.3: Class B.

**Requirements**

* **REQ_RTC_001** The pump shall check clock validity at power up and require the user to confirm the time before basal delivery resumes when validity cannot be established. [Verified by: VER_RTC_001] [Standards: IEC 62304 cl 7.2]

**Design failure considerations**

#### DFC_RTC_01 Clock loses time after battery change

* Failure mode: Clock loses time after a battery change
* Cause: Backup capacitor is depleted during a long battery change
* Hazard: Incorrect therapy settings
* Hazardous situation: The basal schedule is shifted relative to the true time of day
* Harm: Transient hyperglycemia correctable by the user
* Detection before controls: User observation
* Occurrence before controls: Probable
* Risk control: RCM_RTC_01 | Clock validity check at power up that forces user confirmation of the time | protective measure | occurrence 2 | REQ_RTC_001

