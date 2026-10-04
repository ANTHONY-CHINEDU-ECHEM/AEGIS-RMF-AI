# Risk Management Summary. Aurelia P200 Ambulatory Insulin Infusion Pump

Generated on 04 October 2026 by Aegis RMF AI 1.0.0.

## Scope

This summary covers 39 hazard analysis records extracted from 6 design documents describing 23 components, 58 requirements and 57 verification records. Field evidence was drawn from 10024 incident reports. Risks were evaluated against policy RAP_001 revision C.

## Risk profile

* Before risk control: 4 ACCEPTABLE, 28 REVIEW, 7 UNACCEPTABLE
* After risk control: 23 ACCEPTABLE, 15 REVIEW, 1 UNACCEPTABLE
* Total risk priority number fell from 1919 to 703, a reduction of 63.4 percent

## Residual risks that are not acceptable

* RISK_SW_02 Insulin on board not subtracted. Residual severity 4, probability 4, detectability 5, RPN 80, region UNACCEPTABLE. Design release blocked. Source: SRS_003 section 4.1 (DFC_SW_02).
* RISK_CGM_01 False high glucose drives automated correction. Residual severity 5, probability 1, detectability 5, RPN 25, region REVIEW. Benefit risk analysis required. Source: UCS_004 section 4.2 (DFC_CGM_01).
* RISK_COM_01 Unauthorized remote bolus command. Residual severity 5, probability 1, detectability 5, RPN 25, region REVIEW. Benefit risk analysis required. Source: UCS_004 section 4.1 (DFC_COM_01).
* RISK_COM_02 Stale glucose data after connection loss. Residual severity 4, probability 2, detectability 2, RPN 16, region REVIEW. Benefit risk analysis required. Source: UCS_004 section 4.1 (DFC_COM_02).
* RISK_COM_03 Corrupted setting change accepted. Residual severity 5, probability 1, detectability 5, RPN 25, region REVIEW. Benefit risk analysis required. Source: UCS_004 section 4.1 (DFC_COM_03).
* RISK_DRV_01 Continuous motor run from a shorted driver stage. Residual severity 5, probability 1, detectability 2, RPN 10, region REVIEW. Benefit risk analysis required. Source: HDS_002 section 3.1 (DFC_DRV_01).
* RISK_DRV_03 Plunger coupling disengagement and free flow. Residual severity 5, probability 1, detectability 5, RPN 25, region REVIEW. Benefit risk analysis required. Source: HDS_002 section 3.2 (DFC_DRV_03).
* RISK_INF_01 Infusion set connector detachment. Residual severity 4, probability 2, detectability 4, RPN 32, region REVIEW. Benefit risk analysis required. Source: HDS_002 section 5.2 (DFC_INF_01).
* RISK_MCU_02 Corruption of the active delivery rate. Residual severity 5, probability 1, detectability 5, RPN 25, region REVIEW. Benefit risk analysis required. Source: SRS_003 section 3.1 (DFC_MCU_02).
* RISK_MCU_03 Silent failure of the safety supervisor. Residual severity 5, probability 1, detectability 2, RPN 10, region REVIEW. Benefit risk analysis required. Source: SRS_003 section 3.2 (DFC_MCU_03).
* RISK_SNS_03 False occlusion alarms. Residual severity 2, probability 4, detectability 2, RPN 16, region REVIEW. Benefit risk analysis required. Source: HDS_002 section 4.1 (DFC_SNS_03).
* RISK_SNS_04 Encoder undercount. Residual severity 5, probability 1, detectability 2, RPN 10, region REVIEW. Benefit risk analysis required. Source: HDS_002 section 4.2 (DFC_SNS_04).
* RISK_SW_01 Excessive bolus recommendation. Residual severity 5, probability 1, detectability 3, RPN 15, region REVIEW. Benefit risk analysis required. Source: SRS_003 section 4.1 (DFC_SW_01).
* RISK_SW_05 Bolus command executed twice. Residual severity 4, probability 2, detectability 5, RPN 40, region REVIEW. Benefit risk analysis required. Source: SRS_003 section 4.2 (DFC_SW_05).
* RISK_UI_01 Unintended bolus from accidental touch. Residual severity 5, probability 1, detectability 5, RPN 25, region REVIEW. Benefit risk analysis required. Source: UCS_004 section 3.1 (DFC_UI_01).
* RISK_UI_02 Decimal dose entry error. Residual severity 5, probability 1, detectability 4, RPN 20, region REVIEW. Benefit risk analysis required. Source: UCS_004 section 3.1 (DFC_UI_02).

## Field evidence

* RISK_INF_01 Infusion set connector detachment. Engineering probability 3 was raised to 4 because 695 similar incident reports imply a rate of 69.5 per 100000 device years.
* RISK_SW_05 Bolus command executed twice. Engineering probability 2 was raised to 3 because 52 similar incident reports imply a rate of 5.2 per 100000 device years.

## Gap findings

* BLOCKER. G4 control verification not passed. RCM_SW_03 for RISK_SW_02 has verification status FAIL, so no credit was given. Reference: ISO 14971 cl 7.2.
* BLOCKER. G6 unacceptable residual risk. RISK_SW_02 residual risk is UNACCEPTABLE (severity 4, probability 4). Reference: ISO 14971 cl 7.3.
* MAJOR. G1 component without hazard analysis. Component CMP_ACC_01 Belt Clip and Holster has no failure mode analysis, yet 260 similar incident reports exist in field data. Reference: ISO 14971 cl 5.4.
* MAJOR. G2 risk without control. RISK_SNS_03 is in the REVIEW region before control and has no risk control measure. Reference: ISO 14971 cl 7.1.
* MAJOR. G3 control without verification record. RCM_IFU_02 for RISK_RSV_01 has an implementing requirement with no verification record, so no credit was given. Reference: ISO 14971 cl 7.2.
* MAJOR. G4 control verification not passed. RCM_COM_02 for RISK_COM_01 has verification status PENDING, so no credit was given. Reference: ISO 14971 cl 7.2.
* MAJOR. G8 field data exceeds engineering estimate. RISK_INF_01 engineering probability 3 was raised to 4 by 695 similar incident reports. Reference: ISO 14971 cl 10.4.
* MAJOR. G8 field data exceeds engineering estimate. RISK_SW_05 engineering probability 2 was raised to 3 by 52 similar incident reports. Reference: ISO 14971 cl 10.4.
* ACTION. G7 benefit risk analysis required. RISK_CGM_01 residual risk is in the REVIEW region (severity 5, probability 1). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_COM_01 residual risk is in the REVIEW region (severity 5, probability 1). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_COM_02 residual risk is in the REVIEW region (severity 4, probability 2). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_COM_03 residual risk is in the REVIEW region (severity 5, probability 1). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_DRV_01 residual risk is in the REVIEW region (severity 5, probability 1). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_DRV_03 residual risk is in the REVIEW region (severity 5, probability 1). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_INF_01 residual risk is in the REVIEW region (severity 4, probability 2). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_MCU_02 residual risk is in the REVIEW region (severity 5, probability 1). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_MCU_03 residual risk is in the REVIEW region (severity 5, probability 1). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_SNS_03 residual risk is in the REVIEW region (severity 2, probability 4). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_SNS_04 residual risk is in the REVIEW region (severity 5, probability 1). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_SW_01 residual risk is in the REVIEW region (severity 5, probability 1). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_SW_05 residual risk is in the REVIEW region (severity 4, probability 2). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_UI_01 residual risk is in the REVIEW region (severity 5, probability 1). Reference: ISO 14971 cl 7.4.
* ACTION. G7 benefit risk analysis required. RISK_UI_02 residual risk is in the REVIEW region (severity 5, probability 1). Reference: ISO 14971 cl 7.4.

## Standards coverage

* 36 of 46 catalogue clauses have evidence in the file
* No evidence in file for IEC 62304 cl 7.3 Verification of risk control measures
* No evidence in file for IEC 62366 1 cl 5.1 Prepare use specification
* No evidence in file for IEC 62366 1 cl 5.3 Identify known or foreseeable hazards and hazardous situations
* No evidence in file for ISO 13485 cl 8.2.1 Feedback
* No evidence in file for ISO 14971 cl 4.1 Risk management process
* No evidence in file for ISO 14971 cl 4.2 Management responsibilities
* No evidence in file for ISO 14971 cl 4.3 Competence of personnel
* No evidence in file for ISO 14971 cl 4.5 Risk management file
* No evidence in file for ISO 14971 cl 7.6 Completeness of risk control
* No evidence in file for ISO 14971 cl 10.1 Production and post production activities

## Traceability verification

* 113 links from component to requirement and verification were walked forward and backward
* Broken links: 0
