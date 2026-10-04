# Risk Methodology

This document explains how Aegis RMF AI turns a failure scenario into a scored and evaluated risk. All values quoted here are defined in `configs/risk_policy.yaml` and `configs/harm_catalogue.yaml`. The criteria are illustrative. A manufacturer must define and justify its own criteria under ISO 14971 clauses 4.2 and 4.4.

## Three ratings

### Severity (S)

Severity is a property of the harm. The harm text in a design failure consideration is matched against the harm catalogue and the catalogue fixes the rating.

* 1 Negligible: inconvenience or temporary discomfort
* 2 Minor: temporary injury that the user can correct
* 3 Serious: injury that needs professional medical intervention
* 4 Critical: permanent impairment or life threatening injury
* 5 Catastrophic: death or irreversible life altering injury

### Probability (P)

Probability is the probability of occurrence of harm. Two estimates are made and the higher is used.

* The engineering estimate is the occurrence term recorded in the design document.
* The field estimate comes from the incident corpus. The agent counts incident reports whose similarity to the scenario meets the threshold, divides by the assumed exposure and expresses the result per 100000 device years.

Rate bounds per 100000 device years:

* 1 Improbable: below 0.5
* 2 Remote: 0.5 to below 5
* 3 Occasional: 5 to below 50
* 4 Probable: 50 to below 500
* 5 Frequent: 500 and above

Taking the higher value implements the feedback loop of ISO 14971 clause 10: field information that contradicts the original estimate reopens the risk.

### Detectability (D)

Detectability is rated from the means of detection available before harm occurs. A higher rating means the failure is harder to detect.

* 1 Continuous monitoring with automatic safe state
* 2 Continuous monitoring with alarm
* 3 Periodic self test
* 4 User observation
* 5 No detection

## Two decisions, kept separate

### Acceptability: severity and probability only

ISO 14971 defines risk as the combination of the probability of occurrence of harm and the severity of that harm. Acceptability is therefore read from a five by five matrix of severity against probability. Detectability plays no part in it. A test asserts that the acceptability lookup does not accept a detectability argument.

![Risk matrix](images/risk_matrix_before_after.png)

Regions:

* ACCEPTABLE: no further action
* REVIEW: reduce further, or justify by benefit risk analysis under clause 7.4 when further reduction is not practicable
* UNACCEPTABLE: design release is blocked

A Catastrophic harm is never ACCEPTABLE, even at the lowest probability.

### Prioritisation: the three dimensional lookup

The risk priority number is S x P x D. It is a convention from failure mode and effects analysis and is useful for ranking work. It has a known weakness: very different risks can share one number. A severity 5, probability 1, detectability 4 risk and a severity 2, probability 2, detectability 5 risk both score 20.

For that reason the engine also assigns an action priority from a lookup over all three ratings. The lookup is defined by ordered rules, each a lower bound on S, P and D, and is materialised as a tensor of 125 cells. Because each rule is a lower bound, the tensor is monotone by construction, and the policy loader rejects any rule set that would let a worse rating earn a lower priority.

![Action priority cube](images/action_priority_cube.png)

## Crediting risk controls

Each design failure consideration lists its risk control measures. Each control states its type, the rating it claims to reduce, by how many levels, and the requirements that implement it. The engine credits the claims under five rules.

1. Verification gate. A control earns credit only when every requirement that implements it has a passing verification record. A failed, pending or missing record means no credit. This enforces clause 7.2.
2. Priority order. Controls are processed as inherent safety by design, then protective measures, then information for safety, following clause 7.1. Document order does not change who earns the credit.
3. Limits by type. Inherent design may reduce severity by up to 2, probability by up to 3 and detectability by up to 2. A protective measure may reduce probability by up to 2 and detectability by up to 3 and may not reduce severity. Information for safety may reduce probability or detectability by 1 and may not reduce severity.
4. Limit on information for safety. All information for safety controls on one risk share a total credit of 1 level.
5. Limits by dimension and a floor. Total credit is capped at 2 levels for severity and 3 for probability and detectability. No rating falls below 1.

When a claim is reduced by a rule, the reason is recorded in the control credit notes and exported with the matrix.

## Worked example: RISK_SW_02

Source: SRS_003 section 4.1, design failure consideration DFC_SW_02.

* Failure mode: insulin on board is not subtracted from a correction bolus
* Harm: moderate hypoglycemia requiring assistance, severity 4
* Detection before controls: no detection, detectability 5
* Engineering occurrence: Probable, rating 4. Field data matched 398 reports, which implies rating 3, so the engineering estimate stands.
* Before control: 4 x 4 x 5 = 80, region UNACCEPTABLE
* Control: RCM_SW_03, a protective measure claiming 2 levels of probability reduction, implemented by REQ_SW_004 and REQ_SW_005
* Verification: VER_SW_004 passed. VER_SW_005 failed.
* Credit: none, because one implementing requirement failed verification
* After control: 4 x 4 x 5 = 80, region UNACCEPTABLE. Design release blocked.

Had the verification passed, probability would fall to 2 and the residual risk would be 4 x 2 x 5 = 40 in the REVIEW region.

## Simplifications to be aware of

* ISO/TR 24971 describes probability of harm as the product of the probability that a hazardous situation occurs and the probability that it leads to harm. This engine uses a single probability rating.
* One harm is recorded per failure consideration. A scenario with several possible harms needs one consideration for each.
* The incident count depends on the embedding and the similarity threshold. On the labelled synthetic corpus the default settings give a macro precision of 0.98 and a macro recall of 0.81, so field rates are slightly understated.
