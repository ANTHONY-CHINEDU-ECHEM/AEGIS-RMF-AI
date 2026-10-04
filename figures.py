"""Render the figures used in the documentation from a pipeline result."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

from aegis_rmf.graph.base import FORWARD  # noqa: E402

REGION_COLOR = {"ACCEPTABLE": "#c6efce", "REVIEW": "#ffeb9c", "UNACCEPTABLE": "#ffc7ce"}
PRIORITY_COLOR = {0: "#7fbf7f", 1: "#f2c14e", 2: "#d9534f"}
LABEL_COLOR = {
    "Component": "#1f3864", "FailureMode": "#c0504d", "HazardousSituation": "#e46c0a", "Harm": "#7030a0",
    "RiskItem": "#bf9000", "ControlMeasure": "#2e75b6", "Requirement": "#548235", "Verification": "#3a9c9c",
}
NAVY = "#1f3864"


def _save(figure, path: Path) -> Path:
    figure.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return path


def risk_matrix(result, path: Path) -> Path:
    policy = result.policy
    figure, axes = plt.subplots(1, 2, figsize=(14, 5.6))
    for axis, stage, title in ((axes[0], "pre", "Before risk control"), (axes[1], "post", "After risk control")):
        counts = Counter((getattr(r, stage).severity, getattr(r, stage).probability) for r in result.records)
        for s in range(1, 6):
            for p in range(1, 6):
                axis.add_patch(plt.Rectangle((p - 0.5, s - 0.5), 1, 1, facecolor=REGION_COLOR[policy.region(s, p).value], edgecolor="white", linewidth=2))
                if counts.get((s, p)):
                    axis.text(p, s, str(counts[(s, p)]), ha="center", va="center", fontsize=17, fontweight="bold", color=NAVY)
        axis.set_xlim(0.5, 5.5)
        axis.set_ylim(0.5, 5.5)
        axis.set_xticks(range(1, 6), [f"{p}\n{policy.probability_labels[p]}" for p in range(1, 6)])
        axis.set_yticks(range(1, 6), [f"{s} {policy.severity_labels[s]}" for s in range(1, 6)])
        axis.set_xlabel("Probability of harm")
        axis.set_ylabel("Severity of harm")
        axis.set_title(title, fontweight="bold")
        axis.set_aspect("equal")
    figure.suptitle("Risk acceptability matrix: number of risks in each cell", fontsize=14, fontweight="bold")
    figure.subplots_adjust(wspace=0.4)
    return _save(figure, path)


def rpn_chart(result, path: Path) -> Path:
    records = sorted(result.records, key=lambda r: r.pre.rpn)
    figure, axis = plt.subplots(figsize=(11, 12))
    positions = range(len(records))
    axis.barh(positions, [r.pre.rpn for r in records], color="#b8c4d9", label="RPN before control")
    axis.barh(positions, [r.post.rpn for r in records], color=[REGION_COLOR[r.post.region.value] for r in records],
              edgecolor="#555555", linewidth=0.6, label="RPN after control (colour shows residual region)")
    axis.set_yticks(positions, [f"{r.risk_id}  {r.title[:44]}" for r in records], fontsize=8)
    axis.set_xlabel("Risk priority number (severity x probability x detectability)")
    axis.set_title("Risk priority number before and after risk control", fontweight="bold")
    axis.legend(loc="lower right")
    axis.grid(axis="x", alpha=0.3)
    return _save(figure, path)


def priority_cube(result, path: Path) -> Path:
    tensor = result.policy.priority_tensor()
    figure = plt.figure(figsize=(8.5, 7.5))
    axis = figure.add_subplot(projection="3d")
    for rank, name in ((0, "LOW"), (1, "MEDIUM"), (2, "HIGH")):
        points = [(p, d, s) for s in range(1, 6) for p in range(1, 6) for d in range(1, 6) if tensor[s - 1, p - 1, d - 1] == rank]
        axis.scatter(*zip(*points, strict=True), s=150, color=PRIORITY_COLOR[rank], edgecolor="#333333", linewidth=0.4, label=name, depthshade=False)
    axis.set_xlabel("Probability")
    axis.set_ylabel("Detectability")
    axis.set_zlabel("Severity")
    axis.set_xticks(range(1, 6))
    axis.set_yticks(range(1, 6))
    axis.set_zticks(range(1, 6))
    axis.view_init(elev=22, azim=35)
    axis.legend(title="Action priority", loc="upper left")
    axis.set_title("Three dimensional action priority lookup (125 cells)", fontweight="bold")
    return _save(figure, path)


def graph_trace(result, path: Path, component_id: str = "CMP_SW_01") -> Path:
    store = result.store
    layers = ["Component", "FailureMode", "HazardousSituation", "RiskItem", "Harm", "ControlMeasure", "Requirement", "Verification"]
    reached = store.trace(component_id, FORWARD)
    risk_requirements = set()
    for risk_id in reached.get("RiskItem", []):
        for control in store.out(risk_id, "CONTROLLED_BY"):
            risk_requirements.update(node["id"] for node in store.out(control["id"], "IMPLEMENTED_BY"))
    nodes = {component_id: "Component"}
    for label in layers[1:]:
        for node_id in reached.get(label, []):
            if label == "Requirement" and node_id not in risk_requirements:
                continue
            nodes[node_id] = label
    verified = {v["id"] for r in risk_requirements for v in store.out(r, "VERIFIED_BY")}
    nodes = {n: label for n, label in nodes.items() if label != "Verification" or n in verified}
    position: dict[str, tuple[float, float]] = {}

    def anchor(node_id: str) -> float:
        """Mean height of already placed neighbours, used to reduce edge crossings."""
        linked = [n["id"] for direction in ("forward", "backward") for n, _, _ in store.neighbors(node_id, None, direction)]
        heights = [position[n][1] for n in linked if n in position]
        return sum(heights) / len(heights) if heights else 0.0

    for index, label in enumerate(layers):
        members = sorted((n for n, node_label in nodes.items() if node_label == label), key=lambda n: (0 - anchor(n), n))
        for rank, node_id in enumerate(members):
            position[node_id] = (index, (len(members) - 1) / 2 - rank)
    figure, axis = plt.subplots(figsize=(16, 7))
    for node_id in nodes:
        for target, relationship, _ in store.neighbors(node_id, None, FORWARD):
            if target["id"] in nodes and relationship != "HAS_REQUIREMENT":
                (x0, y0), (x1, y1) = position[node_id], position[target["id"]]
                axis.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops={"arrowstyle": "->", "color": "#888888", "lw": 1.0, "shrinkA": 34, "shrinkB": 40})
    for node_id, label in nodes.items():
        x, y = position[node_id]
        axis.text(x, y, node_id, ha="center", va="center", fontsize=8, color="white", fontweight="bold",
                  bbox={"boxstyle": "round,pad=0.35", "facecolor": LABEL_COLOR[label], "edgecolor": "none"})
    for index, label in enumerate(layers):
        axis.text(index, max(y for _, y in position.values()) + 0.9, label, ha="center", fontsize=10, fontweight="bold", color=LABEL_COLOR[label])
    axis.set_xlim(-0.6, len(layers) - 0.4)
    axis.set_ylim(min(y for _, y in position.values()) - 0.7, max(y for _, y in position.values()) + 1.4)
    axis.axis("off")
    axis.set_title(f"Knowledge graph trace for {component_id} {store.get_node(component_id)['name']}", fontweight="bold")
    return _save(figure, path)


def field_evidence(result, path: Path) -> Path:
    records = sorted(result.records, key=lambda r: r.field.matched_count)
    figure, axis = plt.subplots(figsize=(11, 12))
    colors = ["#d9534f" if r.probability_basis == "field evidence" else "#2e75b6" for r in records]
    axis.barh(range(len(records)), [max(r.field.matched_count, 0.8) for r in records], color=colors)
    axis.set_xscale("log")
    axis.set_yticks(range(len(records)), [f"{r.risk_id}  {r.title[:44]}" for r in records], fontsize=8)
    exposure = result.policy.exposure_device_years
    for level in range(1, 5):
        bound = result.policy.probability_rate_bounds[level] * exposure / 100000.0
        axis.axvline(bound, color="#777777", linestyle="--", linewidth=0.8)
        axis.text(bound, len(records) + 0.1, f" {result.policy.probability_labels[level + 1]}", fontsize=8, color="#555555")
    axis.set_ylim(0 - 0.8, len(records) + 0.9)
    axis.set_xlabel("Similar incident reports found by vector search (log scale)")
    axis.set_title("Field evidence per risk. Red bars: field data raised the probability rating", fontweight="bold")
    return _save(figure, path)


def matrix_preview(result, path: Path) -> Path:
    wanted = ["RISK_SW_02", "RISK_INF_01", "RISK_SW_05", "RISK_COM_01", "RISK_DRV_01", "RISK_PWR_02", "RISK_SNS_03", "RISK_RSV_01"]
    rows = [row for row in result.matrix if row.risk_id in wanted] or result.matrix[:8]
    headers = ["Risk", "Component", "Harm", "S P D\nbefore", "RPN\nbefore", "Region before", "Controls", "Requirements",
               "Verification", "S P D\nafter", "RPN\nafter", "Region after", "Design reference"]
    cells = [[
        row.risk_id, row.component_id, row.harm_id.replace("HARM_", ""),
        f"{row.severity_pre} {row.probability_pre} {row.detectability_pre}", row.rpn_pre, row.region_pre,
        "\n".join(row.control_ids) or "none", "\n".join(row.requirement_ids) or "none",
        "\n".join(" ".join(ref.split()[:2]) if ref.startswith("VER") else "no record" for ref in row.verification_refs) or "none",
        f"{row.severity_post} {row.probability_post} {row.detectability_post}", row.rpn_post, row.region_post,
        row.design_refs[0],
    ] for row in rows]
    figure, axis = plt.subplots(figsize=(19, 0.62 * len(rows) + 1.2))
    axis.axis("off")
    table = axis.table(cellText=cells, colLabels=headers, loc="center", cellLoc="left",
                       colWidths=[0.07, 0.07, 0.085, 0.04, 0.04, 0.08, 0.075, 0.08, 0.105, 0.04, 0.04, 0.08, 0.165])
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 3.1)
    for (row_index, _), cell in table.get_celld().items():
        if row_index == 0:
            cell.set_facecolor(NAVY)
            cell.set_text_props(color="white", fontweight="bold")
        elif cell.get_text().get_text() in REGION_COLOR:
            cell.set_facecolor(REGION_COLOR[cell.get_text().get_text()])
    axis.set_title("Traceability matrix extract (selected columns of the full export)", fontweight="bold")
    return _save(figure, path)


def architecture(path: Path) -> Path:
    figure, axis = plt.subplots(figsize=(15, 7.2))
    axis.set_xlim(0, 15)
    axis.set_ylim(0, 7.2)
    axis.axis("off")

    def box(x, y, w, h, title, body, color):
        axis.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", facecolor=color, edgecolor="none"))
        axis.text(x + w / 2, y + h - 0.28, title, ha="center", va="top", fontsize=10, fontweight="bold", color="white")
        axis.text(x + w / 2, y + h - 0.72, body, ha="center", va="top", fontsize=8, color="white")

    def arrow(start, end):
        axis.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "color": "#444444", "lw": 1.6})

    box(0.2, 5.3, 2.6, 1.5, "Design documents", "Architecture, hardware,\nsoftware, usability,\nverification, plan", "#5b6b8c")
    box(0.2, 3.4, 2.6, 1.5, "Incident corpus", "Adverse event reports\n(synthetic corpus)", "#5b6b8c")
    box(0.2, 1.5, 2.6, 1.5, "Catalogues", "Risk policy, harm catalogue,\nstandard clauses", "#5b6b8c")
    box(3.7, 4.4, 2.6, 2.0, "Ingestion", "LlamaIndex parsing\nand chunking with exact\nsection references", NAVY)
    box(3.7, 1.6, 2.6, 2.0, "Qdrant vector index", "Design text, clauses,\nincidents, risk records", "#2e75b6")
    box(7.2, 4.4, 2.6, 2.0, "Scenario extraction", "Rule based parser.\nOptional LLM proposals\nheld for human review", NAVY)
    box(7.2, 1.6, 2.6, 2.0, "Risk scoring agent", "Policy lookups only:\nS x P x D, RPN, region,\ncontrol credit, audit trail", "#c0504d")
    box(10.7, 3.0, 2.2, 2.0, "Neo4j graph", "Component to failure\nmode to hazardous\nsituation to harm\nto control", "#548235")
    box(13.3, 5.5, 1.5, 1.3, "Matrix", "CSV, Excel,\nHTML", "#7030a0")
    box(13.3, 3.9, 1.5, 1.3, "Gap report", "Audit\nfindings", "#7030a0")
    box(13.3, 2.3, 1.5, 1.3, "FastAPI", "Trace, score,\nask", "#7030a0")
    box(13.3, 0.7, 1.5, 1.3, "Evaluation", "Retrieval\nand RAGAS", "#7030a0")
    for start, end in [((2.8, 6.0), (3.7, 5.6)), ((2.8, 4.1), (3.7, 2.9)), ((2.8, 2.2), (3.7, 2.3)), ((5.0, 4.4), (5.0, 3.6)),
                       ((6.3, 5.4), (7.2, 5.4)), ((8.5, 4.4), (8.5, 3.6)), ((6.3, 2.6), (7.2, 2.6)), ((9.8, 2.9), (10.7, 3.7)),
                       ((12.9, 4.6), (13.3, 6.0)), ((12.9, 4.2), (13.3, 4.5)), ((12.9, 3.8), (13.3, 3.0)), ((12.9, 3.3), (13.3, 1.5))]:
        arrow(start, end)
    axis.text(3.0, 2.05, "", fontsize=8)
    axis.set_title("Aegis RMF AI architecture", fontsize=14, fontweight="bold")
    return _save(figure, path)


def render_all(result, directory: Path) -> list[Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return [
        architecture(directory / "architecture.png"),
        risk_matrix(result, directory / "risk_matrix_before_after.png"),
        rpn_chart(result, directory / "rpn_before_after.png"),
        priority_cube(result, directory / "action_priority_cube.png"),
        graph_trace(result, directory / "knowledge_graph_trace.png"),
        field_evidence(result, directory / "field_evidence.png"),
        matrix_preview(result, directory / "traceability_matrix_preview.png"),
    ]
