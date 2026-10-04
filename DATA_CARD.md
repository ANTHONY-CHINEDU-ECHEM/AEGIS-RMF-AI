# Data Card: Synthetic Adverse Event Corpus

## Summary

`synthetic_adverse_events.jsonl` holds 10024 adverse event reports for the fictional Aurelia P200 insulin infusion pump. The file imitates the shape of public medical device reports so that the engine can be exercised on a realistic volume of field evidence without using data about real patients, real products or real manufacturers.

Every record is synthetic. No record describes a real event.

## How it was made

The file is produced by `scripts/generate_incident_corpus.py` with a fixed seed of 14971, so the same command always reproduces the same bytes. The generator holds 42 product problem categories. Each category has a record count, a typical patient problem, a mix of event types (malfunction, injury, death) and between one and three narrative patterns. Narratives are assembled from an opening phrase, a category pattern, a context, an outcome and a follow up sentence.

## Fields

* `report_number`: unique identifier in the form MDR, year, serial
* `date_received`: date in the openFDA layout of year, month and day without separators
* `event_type`: Malfunction, Injury or Death
* `device`: brand name, generic name, model number, software version and device age in months
* `product_problem_code` and `product_problem`: the category label, which is also the ground truth used to measure incident matching
* `patient_problem`: the clinical outcome, or no clinical signs for malfunctions
* `patient_age_group`: Pediatric, Adolescent, Adult or Older adult
* `narrative`: free text description of the event
* `source`: always the value synthetic

## Assumed exposure

The risk policy assumes that the corpus represents 1000000 device years of field exposure. Incident rates are expressed per 100000 device years and are mapped to probability ratings by the bounds in `configs/risk_policy.yaml`.

## Deliberate features

Three features were built in so that the engine has something meaningful to find.

* Connector detachment reports (700) and duplicate bolus reports (120) are more frequent than the engineering estimates in the design documents imply, which should raise the probability rating of two risks.
* Belt clip breakage reports (260) concern a component that has no failure analysis in the design documents.
* Three categories (no fault found, cosmetic damage, belt clip breakage) match no analysed failure mode and act as noise for the matcher.

## Limitations

Narratives within a category share vocabulary, which makes them easier to match than real reports. Real reports are longer, noisier, often incomplete and frequently describe several problems at once. Matching precision and recall measured on this corpus are therefore an upper bound on what should be expected from real field data.

## Using real data

`scripts/fetch_openfda_maude.py` downloads real reports from the openFDA device event API and writes them in the same layout. Set `incidents_path` in `configs/settings.yaml` to the downloaded file. Real reports carry no ground truth category, so the incident matching evaluation is skipped for them.
