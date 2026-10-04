"""Generate the synthetic adverse event corpus used as historical field evidence.

The corpus imitates the shape of public adverse event reports for insulin infusion pumps.
Every record is synthetic and is labelled as such. The generator is seeded, so the same
command always produces the same file.

Usage:
    python scripts/generate_incident_corpus.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 14971
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "incidents" / "synthetic_adverse_events.jsonl"

HYPO_S = "Severe hypoglycemia"
HYPO_M = "Hypoglycemia"
DKA = "Diabetic ketoacidosis"
HYPER = "Hyperglycemia"
NONE = "No clinical signs or symptoms"

# code: (product problem label, record count, patient problem, (malfunction, injury, death) weights, core sentences)
CATEGORIES: dict[str, tuple[str, int, str, tuple[float, float, float], list[str]]] = {
    "PP_MOTOR_RUNAWAY": ("Motor runs continuously", 18, HYPO_S, (0.3, 0.6, 0.1), [
        "the pump motor ran continuously and delivered insulin beyond the programmed dose {context}",
        "the motor kept running after the bolus completed and the reservoir emptied into the patient {context}",
        "a shorted motor driver stage caused continuous motor run and overdelivery of insulin {context}"]),
    "PP_MOTOR_STALL": ("Motor stall or failure to advance", 240, DKA, (0.7, 0.3, 0.0), [
        "the motor stalled and the plunger did not advance, so basal insulin was not delivered for several hours {context}",
        "the pump displayed normal delivery but the plunger had not moved and no alarm was raised {context}",
        "the drive motor lost torque and the plunger stopped advancing during basal delivery {context}"]),
    "PP_COUPLING_DISENGAGE": ("Plunger coupling disengaged", 14, HYPO_S, (0.3, 0.65, 0.05), [
        "the plunger coupling disengaged from the drive nut and the reservoir contents siphoned into the patient {context}",
        "the coupling latch fractured and insulin flowed freely when the pump was held above the infusion site {context}"]),
    "PP_DOSE_INACCURACY": ("Inaccurate delivery volume", 210, HYPER, (0.85, 0.15, 0.0), [
        "delivered basal volume was lower than the programmed volume over several days {context}",
        "lead screw wear was found and small basal increments were delivered inaccurately {context}",
        "the patient noticed that the reservoir emptied more slowly than the programmed basal rate implied {context}"]),
    "PP_OCCLUSION_UNDETECTED": ("Occlusion not detected", 260, DKA, (0.55, 0.45, 0.0), [
        "the infusion line was blocked and insulin was not delivered but no occlusion alarm sounded {context}",
        "a downstream occlusion was not detected by the force sensor and the patient received no insulin {context}",
        "the cannula was kinked and blocked for hours and the pump failed to alarm for the occlusion {context}"]),
    "PP_OCCLUSION_RELEASE_BOLUS": ("Unintended bolus after occlusion", 130, HYPO_M, (0.5, 0.5, 0.0), [
        "an occlusion cleared suddenly and insulin that had accumulated in the line was delivered as an unintended bolus {context}",
        "the kinked cannula straightened and the stored insulin was released at once after the occlusion {context}"]),
    "PP_FALSE_OCCLUSION_ALARM": ("False occlusion alarm", 820, HYPER, (0.93, 0.07, 0.0), [
        "the pump raised repeated occlusion alarms when no occlusion was present and delivery stopped each time {context}",
        "false occlusion alarms from force sensor noise interrupted delivery several times {context}",
        "the user changed the infusion set three times for occlusion alarms although no blockage was found {context}"]),
    "PP_ENCODER_FAULT": ("Encoder count error", 20, HYPO_S, (0.5, 0.45, 0.05), [
        "the encoder undercounted motor rotation and the controller commanded extra motor steps, delivering more insulin than programmed {context}",
        "contamination on the optical encoder disc caused an undercount of rotation and overdelivery {context}"]),
    "PP_RESERVOIR_LEAK": ("Reservoir leak", 330, DKA, (0.65, 0.35, 0.0), [
        "insulin leaked from the reservoir seal into the reservoir compartment instead of reaching the patient {context}",
        "the reservoir barrel was cracked and the compartment was wet with insulin while the dose counter recorded delivery {context}",
        "the O ring seal of the reservoir leaked and the patient smelled insulin around the pump {context}"]),
    "PP_AIR_IN_LINE": ("Air in line", 760, HYPER, (0.9, 0.1, 0.0), [
        "air bubbles in the reservoir were delivered in place of insulin {context}",
        "the user saw large air bubbles in the infusion line after priming with cold insulin {context}",
        "air displaced insulin in the infusion line during basal delivery after incomplete priming {context}"]),
    "PP_STERILITY_BREACH": ("Package seal breached", 16, "Infusion site infection", (0.6, 0.4, 0.0), [
        "the sterile barrier pouch of the reservoir had a damaged seal before use {context}",
        "the reservoir package was found open on delivery and the fluid path may have been contaminated {context}"]),
    "PP_CONNECTOR_DETACH": ("Infusion set connector detached", 700, DKA, (0.6, 0.4, 0.0), [
        "the infusion set connector detached from the reservoir and insulin was pumped onto the skin and clothing with no alarm {context}",
        "the connector was not fully locked and came loose, so insulin leaked at the connection instead of entering the tissue {context}",
        "the infusion set connector latch did not engage and the set detached from the reservoir {context}"]),
    "PP_BATTERY_OVERHEAT": ("Battery overheating", 22, "Burn", (0.6, 0.4, 0.0), [
        "the pump became very hot against the body and the battery cell was found swollen {context}",
        "the battery entered thermal runaway and the pump surface temperature rose rapidly while worn {context}"]),
    "PP_BATTERY_SUDDEN_DEPLETION": ("Battery depleted without warning", 310, DKA, (0.7, 0.3, 0.0), [
        "the battery depleted suddenly without a low battery warning and the pump shut down, stopping basal delivery {context}",
        "the pump shut down during sleep with no low battery alarm and delivery stopped for several hours {context}",
        "an aged battery lost capacity abruptly in cold weather and the pump powered off without warning {context}"]),
    "PP_FUEL_GAUGE_ERROR": ("Battery level indication error", 180, DKA, (0.75, 0.25, 0.0), [
        "the displayed battery level stayed at a normal level until the pump shut down abruptly {context}",
        "the fuel gauge overestimated remaining battery capacity and the pump powered off while showing half charge {context}"]),
    "PP_CHARGER_SHOCK": ("Electrical fault during charging", 6, "Electric shock", (0.5, 0.5, 0.0), [
        "the patient felt an electric shock from the enclosure while charging the pump from a damaged USB power source {context}"]),
    "PP_SPEAKER_FAILURE": ("No audible alarm", 150, DKA, (0.7, 0.3, 0.0), [
        "the speaker failed and the audible alarm was silent, so an occlusion alarm on the display was not heard during sleep {context}",
        "the pump showed a low battery alarm on the display but produced no sound because the speaker had an open circuit {context}"]),
    "PP_ALARM_NOT_HEARD": ("Alarm not perceived by user", 640, HYPER, (0.8, 0.2, 0.0), [
        "the alarm volume was too low and the user did not hear a no delivery alarm while the pump was under clothing and bedding {context}",
        "the alarm sounded but was muffled and not heard, and delivery remained stopped {context}",
        "the user slept through the alarm because the volume was insufficient {context}"]),
    "PP_WATER_INGRESS": ("Moisture or water ingress", 280, DKA, (0.75, 0.25, 0.0), [
        "water entered the electronics compartment after swimming and the pump stopped delivery without a valid alarm {context}",
        "moisture was found inside the pump after a drop damaged the gasket and the electronics short circuited {context}",
        "the pump was immersed and water ingress caused it to shut down {context}"]),
    "PP_CRACKED_CASE": ("Cracked enclosure", 35, "Skin laceration", (0.9, 0.1, 0.0), [
        "the enclosure cracked after a drop onto a hard surface and a sharp edge of the case rubbed against the skin {context}",
        "the pump case cracked from impact damage and exposed a sharp edge {context}"]),
    "PP_FIRMWARE_HANG": ("Device freeze or unresponsive", 200, DKA, (0.75, 0.25, 0.0), [
        "the pump firmware hung during delivery, the display froze and no alarm was raised {context}",
        "the display froze and delivery halted until the battery was removed, with no alarm {context}",
        "the main controller stopped responding during a bolus and delivery halted {context}"]),
    "PP_RATE_CORRUPTION": ("Delivery rate data corruption", 9, HYPO_S, (0.3, 0.6, 0.1), [
        "memory corruption altered the active delivery rate and the pump delivered at a rate many times higher than programmed {context}"]),
    "PP_SUPERVISOR_FAULT": ("Safety monitor fault", 3, NONE, (1.0, 0.0, 0.0), [
        "service testing found that the safety supervisor had stopped monitoring and the fault had remained latent {context}"]),
    "PP_BOLUS_CALC_ERROR": ("Incorrect bolus calculation", 90, HYPO_S, (0.45, 0.5, 0.05), [
        "the bolus calculator recommended an excessive dose several times larger than needed and the user accepted it {context}",
        "a glucose unit conversion error caused the bolus calculator to recommend an excessive correction dose {context}"]),
    "PP_IOB_STACKING": ("Insulin on board error", 560, HYPO_M, (0.5, 0.5, 0.0), [
        "insulin on board was not subtracted from a correction bolus after a clock change and repeated correction boluses stacked {context}",
        "the active insulin time was reset to default after a software update, so earlier insulin was ignored and corrections stacked {context}",
        "the pump showed zero insulin on board shortly after a bolus and the next correction bolus was too large {context}"]),
    "PP_SCHEDULE_TIME_SHIFT": ("Basal schedule time error", 140, HYPO_M, (0.6, 0.4, 0.0), [
        "the basal schedule was applied to the wrong time segment after a time zone change, so the overnight rate was delivered during the day {context}",
        "after a clock change the scheduler delivered the daytime basal rate overnight {context}"]),
    "PP_SUSPEND_NOT_RESUMED": ("Delivery did not resume", 230, DKA, (0.65, 0.35, 0.0), [
        "suspended delivery did not resume after the alarm was acknowledged and the pump remained suspended {context}",
        "the user believed delivery had resumed but the pump remained suspended for hours {context}",
        "delivery stayed suspended after a temporary suspension ended {context}"]),
    "PP_DOUBLE_BOLUS": ("Duplicate bolus delivered", 120, HYPO_M, (0.5, 0.5, 0.0), [
        "a bolus command was executed twice after a communication retry and a single bolus request delivered double the intended dose {context}",
        "the history showed the same bolus delivered twice from one request {context}"]),
    "PP_ALARM_SUPPRESSED": ("Alarm not annunciated", 15, DKA, (0.6, 0.4, 0.0), [
        "a high priority occlusion alarm was suppressed by lower priority alarms in the queue and was not annunciated {context}"]),
    "PP_SETTINGS_RESET": ("Settings lost or reset", 190, HYPO_M, (0.65, 0.35, 0.0), [
        "therapy settings reverted to factory defaults after a power loss and the pump resumed with a default basal profile {context}",
        "the basal profile no longer matched the prescription because settings were reset after a battery change {context}"]),
    "PP_CLOCK_RESET": ("Clock or date error", 600, HYPER, (0.92, 0.08, 0.0), [
        "the clock lost time after a battery change and the basal schedule was shifted relative to the true time of day {context}",
        "the pump time was wrong after a long battery change because the backup capacitor was depleted {context}",
        "the clock reset to midnight after the battery was replaced {context}"]),
    "PP_UNINTENDED_KEYPRESS": ("Unintended activation", 110, HYPO_S, (0.5, 0.47, 0.03), [
        "an unintended touch on the touchscreen in a pocket started a bolus without the intent of the user {context}",
        "pressure on the touchscreen during sleep activated the keys and a bolus was started {context}"]),
    "PP_DOSE_ENTRY_ERROR": ("Use error in dose entry", 170, HYPO_S, (0.4, 0.57, 0.03), [
        "the user entered a bolus dose with a misplaced decimal point and a bolus ten times larger than intended was delivered {context}",
        "a caregiver made a tenfold dose entry error on the numeric entry screen and confirmed the bolus {context}"]),
    "PP_DISPLAY_FAILURE": ("Display failure", 270, HYPER, (0.9, 0.1, 0.0), [
        "the display became unreadable after backlight failure and the user could not read alarm text or verify bolus entries {context}",
        "the display panel cracked and the screen was unreadable {context}",
        "the screen went blank while the pump continued to vibrate for an alarm that could not be read {context}"]),
    "PP_UNAUTHORIZED_COMMAND": ("Unauthorized command", 4, NONE, (1.0, 0.0, 0.0), [
        "a security researcher demonstrated that an unauthorized remote bolus command was accepted through weak pairing authentication {context}"]),
    "PP_CONNECTIVITY_LOSS": ("Loss of wireless connection", 720, HYPO_M, (0.88, 0.12, 0.0), [
        "the connection to the glucose sensor was lost and glucose values stopped updating, and the user dosed on a stale glucose value {context}",
        "radio interference interrupted the connection and the pump showed a stale glucose reading {context}",
        "the transmitter was out of range and the glucose value on the pump no longer reflected the current level {context}"]),
    "PP_CORRUPT_DATA": ("Corrupted data accepted", 12, HYPO_S, (0.5, 0.5, 0.0), [
        "a corrupted data packet was accepted as a valid setting change and the basal profile was updated with corrupted values {context}"]),
    "PP_CGM_FALSE_HIGH": ("Incorrect glucose value used", 100, HYPO_S, (0.45, 0.5, 0.05), [
        "a falsely high glucose reading from a sensor compression artifact was used for automated correction "
        "and insulin was delivered against the false high reading {context}",
        "automated correction dosed on a false high glucose reading after a calibration error {context}"]),
    "PP_SET_OVERWEAR": ("Use beyond labeled interval", 540, "Infusion site infection", (0.3, 0.7, 0.0), [
        "the infusion set was worn beyond the recommended change interval because the instructions were misunderstood {context}",
        "the user did not understand the instructions on the infusion set change interval and wore the set for six days {context}",
        "an infusion site infection developed after the set was worn beyond the labeled interval {context}"]),
    "PP_CLIP_BREAK": ("Belt clip broke", 260, NONE, (0.97, 0.03, 0.0), [
        "the belt clip broke and the pump fell to the floor, pulling out the infusion set {context}",
        "the holster clip snapped and the pump dropped {context}"]),
    "PP_NO_FAULT_FOUND": ("No fault found", 300, NONE, (1.0, 0.0, 0.0), [
        "the user requested a replacement pump for a general concern and no specific malfunction was described {context}",
        "the customer asked for help with menu navigation and no device problem was identified {context}"]),
    "PP_COSMETIC": ("Cosmetic damage", 240, NONE, (1.0, 0.0, 0.0), [
        "the screen protector was scratched and the customer asked for a replacement {context}",
        "paint wore off the keys and the labels on the case faded {context}"]),
}

OPENINGS = ["It was reported that", "The customer reported that", "A caregiver reported that",
            "The patient stated that", "A healthcare professional reported that", "According to the complaint,"]
CONTEXTS = ["during the night", "while the patient was at work", "while the patient was at school", "during exercise",
            "while traveling", "after a meal", "in the early morning", "during a weekend trip", "at home in the evening",
            "shortly after a reservoir change"]
MALFUNCTION_OUTCOMES = ["No patient injury was reported.", "The patient monitored glucose closely and no adverse effect occurred.",
                        "The user switched to injections as a backup and no harm resulted.",
                        "Glucose stayed within range and no medical intervention was needed."]
INJURY_TREATMENT = ["was treated in the emergency department", "was admitted to hospital overnight",
                    "was treated by paramedics at home", "was treated with glucagon by a family member",
                    "attended an urgent care clinic", "was treated by the diabetes care team"]
FOLLOW_UPS = ["The pump was returned for evaluation.", "The pump was replaced under warranty.",
              "Customer support guided the user through troubleshooting.", "The device was not returned for evaluation.",
              "Evaluation of the returned device confirmed the reported problem.",
              "Evaluation of the returned device could not reproduce the problem."]
AGE_GROUPS = ["Pediatric", "Adolescent", "Adult", "Adult", "Adult", "Older adult"]
SOFTWARE_VERSIONS = ["2.1.0", "2.2.4", "2.3.1", "2.3.1", "2.4.0", "3.0.2"]


def build_record(rng: random.Random, serial: int, code: str) -> dict:
    label, _, patient_problem, mix, cores = CATEGORIES[code]
    event_type = rng.choices(["Malfunction", "Injury", "Death"], weights=mix)[0]
    core = rng.choice(cores).format(context=rng.choice(CONTEXTS))
    if event_type == "Malfunction":
        outcome, problem = rng.choice(MALFUNCTION_OUTCOMES), NONE
    elif event_type == "Injury":
        problem = patient_problem
        outcome = f"The patient experienced {patient_problem.lower()} and {rng.choice(INJURY_TREATMENT)}."
    else:
        problem = patient_problem
        outcome = f"The patient experienced {patient_problem.lower()}, was found unresponsive and later died."
    narrative = f"{rng.choice(OPENINGS)} {core}. {outcome} {rng.choice(FOLLOW_UPS)}"
    year = rng.choice([2021, 2022, 2023, 2024, 2025])
    return {
        "report_number": f"MDR_{year}_{serial:06d}",
        "date_received": f"{year}{rng.randint(1, 12):02d}{rng.randint(1, 28):02d}",
        "event_type": event_type,
        "device": {
            "brand_name": "Aurelia P200",
            "generic_name": "Pump, infusion, insulin",
            "model_number": "P200",
            "software_version": rng.choice(SOFTWARE_VERSIONS),
            "device_age_months": rng.randint(1, 48),
        },
        "product_problem_code": code,
        "product_problem": label,
        "patient_problem": problem,
        "patient_age_group": rng.choice(AGE_GROUPS),
        "narrative": narrative,
        "source": "synthetic",
    }


def generate() -> list[dict]:
    rng = random.Random(SEED)
    plan = [code for code, spec in CATEGORIES.items() for _ in range(spec[1])]
    rng.shuffle(plan)
    return [build_record(rng, serial, code) for serial, code in enumerate(plan, start=1)]


def main() -> None:
    records = generate()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    print(f"Wrote {len(records)} synthetic adverse event records to {OUTPUT}")


if __name__ == "__main__":
    main()
