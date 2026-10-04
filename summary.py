"""Write the risk management summary report in markdown."""
from __future__ import annotations

from pathlib import Path


def write_summary(path: Path, result, generated: str) -> Path:
    summary = result.summary()
    policy = result.policy
    lines = [
        f"# Risk Management Summary. {summary['device']}", "", generated + ".", "",
        "## Scope", "",
        f"This summary covers {summary['risks']} hazard analysis records extracted from {summary['documents']} design documents "
        f"describing {summary['components']} components, {summary['requirements']} requirements and "
        f"{summary['verification_records']} verification records. Field evidence was drawn from "
        f"{summary['incident_reports']} incident reports. Risks were evaluated against policy {policy.policy_id} revision {policy.revision}.", "",
        "## Risk profile", "",
    ]
    for stage, key in (("Before risk control", "regions_before_control"), ("After risk control", "regions_after_control")):
        counts = ", ".join(f"{count} {region}" for region, count in summary[key].items())
        lines.append(f"* {stage}: {counts}")
    lines += [
        f"* Total risk priority number fell from {summary['total_rpn_before_control']} to {summary['total_rpn_after_control']}, "
        f"a reduction of {summary['total_rpn_reduction_pct']} percent", "",
        "## Residual risks that are not acceptable", "",
    ]
    open_risks = sorted((r for r in result.records if r.post.region.value != "ACCEPTABLE"), key=lambda r: (r.post.region.value != "UNACCEPTABLE", r.risk_id))
    for record in open_risks:
        lines.append(
            f"* {record.risk_id} {record.title}. Residual severity {record.post.severity}, probability {record.post.probability}, "
            f"detectability {record.post.detectability}, RPN {record.post.rpn}, region {record.post.region.value}. {record.disposition}. "
            f"Source: {record.source.label()}."
        )
    lines += ["", "## Field evidence", ""]
    escalated = [r for r in result.records if r.probability_basis == "field evidence"]
    if escalated:
        for record in escalated:
            lines.append(
                f"* {record.risk_id} {record.title}. Engineering probability {record.engineering_probability} was raised to "
                f"{record.pre.probability} because {record.field.matched_count} similar incident reports imply a rate of "
                f"{record.field.rate_per_100k_device_years} per 100000 device years."
            )
    else:
        lines.append("* No engineering estimate was exceeded by field data.")
    lines += ["", "## Gap findings", ""]
    for gap in result.gaps:
        lines.append(f"* {gap.level}. {gap.rule}. {gap.message}. Reference: {gap.clause}.")
    missing = [c for c in result.coverage if c.status != "Evidenced"]
    lines += [
        "", "## Standards coverage", "",
        f"* {len(result.coverage) - len(missing)} of {len(result.coverage)} catalogue clauses have evidence in the file",
    ]
    for clause in missing:
        lines.append(f"* No evidence in file for {clause.key} {clause.topic}")
    lines += [
        "", "## Traceability verification", "",
        f"* {result.bidirectional['links_checked']} links from component to requirement and verification were walked forward and backward",
        f"* Broken links: {len(result.bidirectional['broken_links'])}", "",
    ]
    Path(path).write_text("\n".join(lines), encoding="utf8")
    return path
