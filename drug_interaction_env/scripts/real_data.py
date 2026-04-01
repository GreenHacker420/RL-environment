from __future__ import annotations

import csv
from dataclasses import dataclass
import random
import re
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tasks import TaskConfig, normalize_drug_name


_DRUG1_ALIASES = ("drug1", "drug_1", "drug_a", "drugname1", "drug_name_1", "drug 1")
_DRUG2_ALIASES = ("drug2", "drug_2", "drug_b", "drugname2", "drug_name_2", "drug 2")
_EVENT_ALIASES = (
    "event_name",
    "event",
    "side_effect_name",
    "condition",
    "ddi_type",
    "interaction_description",
    "interaction description",
    "description",
)
_COUNT_ALIASES = ("event_count", "count", "cases", "occurrence", "frequency", "freq")

_SEVERITY_ORDER = {"none": 0, "mild": 1, "moderate": 2, "severe": 3}
_OUTCOME_BY_SEVERITY = {
    "mild": "dose separation",
    "moderate": "close monitoring",
    "severe": "hospitalization",
}
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "acute",
    "adverse",
    "after",
    "agent",
    "and",
    "associated",
    "caused",
    "decreased",
    "effect",
    "effects",
    "elevated",
    "failure",
    "from",
    "increase",
    "increased",
    "interaction",
    "level",
    "levels",
    "major",
    "medication",
    "moderate",
    "mild",
    "patient",
    "patients",
    "reaction",
    "reported",
    "risk",
    "severe",
    "syndrome",
    "the",
    "toxicity",
    "with",
}
_SEVERE_EVENT_KEYWORDS = (
    "bleed",
    "hemorrhage",
    "rhabdomyolysis",
    "respiratory depression",
    "respiratory failure",
    "shock",
    "arrhythmia",
    "torsade",
    "seizure",
    "serotonin syndrome",
    "hyperkalemia",
    "anaphylaxis",
    "death",
    "suicide",
    "myelosuppression",
    "renal failure",
    "kidney injury",
)
_MODERATE_EVENT_KEYWORDS = (
    "hypotension",
    "bradycardia",
    "syncope",
    "kidney",
    "renal",
    "myopathy",
    "hepatotoxic",
    "hepatitis",
    "lactic acidosis",
    "thrombosis",
    "pregnancy",
    "withdrawal",
    "overdose",
    "infection",
    "hypoglycemia",
)
_MILD_EVENT_KEYWORDS = (
    "nausea",
    "vomiting",
    "diarrhea",
    "headache",
    "dizziness",
    "rash",
    "sedation",
    "absorption",
    "chelation",
    "treatment failure",
)
_SEVERE_DESCRIPTION_KEYWORDS = (
    "contraindicated",
    "life-threatening",
    "fatal",
    "death",
    "major bleeding",
    "hemorrhage",
    "rhabdomyolysis",
    "serotonin syndrome",
    "respiratory depression",
    "respiratory failure",
    "cardiac arrest",
    "torsade",
    "arrhythmia",
    "qt prolongation",
    "seizure",
    "shock",
)
_MODERATE_DESCRIPTION_KEYWORDS = (
    "increase the serum concentration",
    "increase serum concentration",
    "decrease the metabolism",
    "decrease metabolism",
    "increase the adverse effects",
    "increase adverse effects",
    "increase the anticoagulant activities",
    "increase the hypoglycemic activities",
    "increase the central nervous system depressant",
    "hyperkalemia",
    "nephrotoxic",
    "myopathy",
    "monitor",
    "avoid combination",
)
_MILD_DESCRIPTION_KEYWORDS = (
    "decrease the absorption",
    "increase the photosensitizing activities",
    "increase photosensitizing activities",
    "decrease excretion rate",
    "decrease therapeutic efficacy",
    "sedative activities",
)
_SUPPORTED_DATASET_EXTENSIONS = (
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
    ".xml",
    ".parquet",
    ".feather",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".db3",
    ".s3db",
    ".dl3",
    ".xls",
    ".xlsx",
    ".xlsm",
    ".xlsb",
    ".odf",
    ".ods",
    ".odt",
)


@dataclass(frozen=True)
class RealInteractionRecord:
    drug1: str
    drug2: str
    event_name: str
    count: float


def _pick_field(row: dict[str, str], aliases: tuple[str, ...]) -> str:
    lowered = {key.lower(): value for key, value in row.items()}
    for alias in aliases:
        value = lowered.get(alias)
        if value:
            return value.strip()
    return ""


def _parse_count(raw_value: str) -> float:
    if not raw_value:
        return 1.0
    cleaned = raw_value.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 1.0


def infer_severity_from_event(event_name: str, count: float) -> str:
    lowered = event_name.lower()
    if any(keyword in lowered for keyword in _SEVERE_EVENT_KEYWORDS):
        return "severe"
    if any(keyword in lowered for keyword in _MODERATE_EVENT_KEYWORDS):
        return "moderate"
    if any(keyword in lowered for keyword in _MILD_EVENT_KEYWORDS):
        return "mild"
    if count >= 500:
        return "severe"
    if count >= 100:
        return "moderate"
    return "mild"


def infer_severity_from_description(description: str) -> str:
    lowered = description.lower()
    if any(keyword in lowered for keyword in _SEVERE_DESCRIPTION_KEYWORDS):
        return "severe"
    if any(keyword in lowered for keyword in _MODERATE_DESCRIPTION_KEYWORDS):
        return "moderate"
    if any(keyword in lowered for keyword in _MILD_DESCRIPTION_KEYWORDS):
        return "mild"
    if "increase" in lowered and "activities" in lowered:
        return "moderate"
    if "decrease" in lowered and ("absorption" in lowered or "efficacy" in lowered):
        return "mild"
    return "moderate"


def extract_keywords(events: list[str], max_keywords: int = 5) -> list[str]:
    scores: dict[str, int] = defaultdict(int)
    for event in events:
        for token in _TOKEN_RE.findall(event.lower()):
            if len(token) < 4 or token in _STOPWORDS:
                continue
            scores[token] += 1
    return [
        token
        for token, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:max_keywords]
    ]


def records_from_rows(
    rows: list[dict[str, Any]],
    limit: int | None = None,
) -> list[RealInteractionRecord]:
    records: list[RealInteractionRecord] = []
    for row in rows:
        normalized_row = {str(key): "" if value is None else str(value) for key, value in row.items()}
        drug1 = normalize_drug_name(_pick_field(normalized_row, _DRUG1_ALIASES))
        drug2 = normalize_drug_name(_pick_field(normalized_row, _DRUG2_ALIASES))
        event_name = _pick_field(normalized_row, _EVENT_ALIASES).lower()
        count = _parse_count(_pick_field(normalized_row, _COUNT_ALIASES))
        if not drug1 or not drug2 or not event_name or drug1 == drug2:
            continue
        records.append(
            RealInteractionRecord(
                drug1=drug1,
                drug2=drug2,
                event_name=event_name,
                count=count,
            )
        )
        if limit is not None and len(records) >= limit:
            break
    return records


def load_twosides_records(csv_path: str | Path, limit: int | None = None) -> list[RealInteractionRecord]:
    with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        records = records_from_rows(list(reader), limit=limit)
    if not records:
        raise ValueError(f"No usable interaction rows found in {csv_path}.")
    return records


def load_kagglehub_records(
    dataset_handle: str,
    file_path: str = "",
    limit: int | None = None,
) -> list[RealInteractionRecord]:
    try:
        import kagglehub
    except ImportError as exc:
        raise RuntimeError(
            "kagglehub is required for --kaggle-dataset. Install it with "
            "`pip install kagglehub[pandas-datasets]`."
        ) from exc
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError(
            "pandas is required for Kaggle dataset loading. Install it with "
            "`pip install kagglehub[pandas-datasets]`."
        ) from exc

    dataset_dir = Path(kagglehub.dataset_download(dataset_handle))
    resolved_file = Path(file_path) if file_path else Path(discover_kagglehub_file(dataset_dir))
    if not resolved_file.is_absolute():
        resolved_file = dataset_dir / resolved_file
    if not resolved_file.exists():
        raise RuntimeError(
            f"The selected Kaggle dataset file does not exist: {resolved_file}. "
            "Pass --kaggle-file-path with a valid path inside the downloaded dataset."
        )

    suffix = resolved_file.suffix.lower()
    if suffix == ".csv":
        dataframe = pd.read_csv(resolved_file)
    elif suffix == ".tsv":
        dataframe = pd.read_csv(resolved_file, sep="\t")
    elif suffix in {".parquet", ".feather"}:
        dataframe = pd.read_parquet(resolved_file)
    elif suffix in {".json", ".jsonl"}:
        dataframe = pd.read_json(resolved_file, lines=suffix == ".jsonl")
    else:
        raise RuntimeError(
            f"Unsupported selected Kaggle dataset file format: {resolved_file.suffix}. "
            "Use --kaggle-file-path to select a csv, tsv, json, jsonl, parquet, or feather file."
        )

    records = records_from_rows(dataframe.to_dict(orient="records"), limit=limit)
    if not records:
        raise ValueError(
            f"No usable interaction rows were loaded from Kaggle dataset {dataset_handle!r} "
            f"file {resolved_file}."
        )
    return records


def discover_kagglehub_file(dataset_dir: Path) -> str:
    candidates = [
        path
        for path in dataset_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in _SUPPORTED_DATASET_EXTENSIONS
    ]
    if not candidates:
        raise RuntimeError(
            f"No supported tabular files were found in downloaded Kaggle dataset directory {dataset_dir}."
        )

    def score(path: Path) -> tuple[int, int, str]:
        lowered = path.name.lower()
        name_score = 0
        for token in ("twosides", "interaction", "drug", "ddi", "side_effect"):
            if token in lowered:
                name_score += 1
        suffix_priority = 0 if path.suffix.lower() == ".csv" else 1
        return (-name_score, suffix_priority, lowered)

    return str(sorted(candidates, key=score)[0])


def compile_interaction_db(
    records: list[RealInteractionRecord],
    allowed_drugs: set[str] | None = None,
    min_count: float = 1.0,
) -> list[dict[str, Any]]:
    pair_events: dict[frozenset[str], list[RealInteractionRecord]] = defaultdict(list)
    for record in records:
        if allowed_drugs is not None:
            if record.drug1 not in allowed_drugs or record.drug2 not in allowed_drugs:
                continue
        if record.count < min_count:
            continue
        pair_events[frozenset({record.drug1, record.drug2})].append(record)

    compiled: list[dict[str, Any]] = []
    for key, pair_records in pair_events.items():
        ordered_drugs = sorted(key)
        events_sorted = sorted(pair_records, key=lambda item: (-item.count, item.event_name))
        severities = []
        for item in pair_records:
            if item.count > 1.0:
                severities.append(infer_severity_from_event(item.event_name, item.count))
            else:
                severities.append(infer_severity_from_description(item.event_name))
        severity = max(severities, key=lambda value: _SEVERITY_ORDER[value])
        dominant = events_sorted[0]
        event_names = [item.event_name for item in events_sorted]
        compiled.append(
            {
                "drug1": ordered_drugs[0],
                "drug2": ordered_drugs[1],
                "severity": severity,
                "interaction_type": "dataset-derived",
                "mechanism": f"dataset-derived safety signal centered on {dominant.event_name}",
                "keywords": extract_keywords(event_names),
                "adverse_events": event_names[:5],
                "clinical_outcome": _OUTCOME_BY_SEVERITY[severity],
                "supporting_event_count": round(sum(item.count for item in pair_records), 2),
            }
        )

    compiled.sort(
        key=lambda item: (
            -_SEVERITY_ORDER[item["severity"]],
            -float(item["supporting_event_count"]),
            item["drug1"],
            item["drug2"],
        )
    )
    return compiled


def build_easy_eval_tasks(
    interaction_db: list[dict[str, Any]],
    limit: int = 50,
) -> list[TaskConfig]:
    tasks: list[TaskConfig] = []
    for index, pair in enumerate(interaction_db[:limit], start=1):
        tasks.append(
            TaskConfig(
                id=f"real-easy-{index:03d}",
                task_type="easy",
                prompt=(
                    f"A patient is taking both {pair['drug1']} and {pair['drug2']}. "
                    "Based on real-world interaction data, what is the severity of the "
                    "drug-drug interaction? Provide a short explanation of the likely risk."
                ),
                input_data={"drug1": pair["drug1"], "drug2": pair["drug2"]},
                ground_truth={
                    "drug1": pair["drug1"],
                    "drug2": pair["drug2"],
                    "severity": pair["severity"],
                    "required_keywords": list(pair["keywords"]),
                    "adverse_events": list(pair["adverse_events"]),
                    "mechanism": pair["mechanism"],
                    "clinical_outcome": pair["clinical_outcome"],
                },
                max_steps=1,
                difficulty_score=0.35,
            )
        )
    return tasks


def build_medium_eval_tasks(
    interaction_db: list[dict[str, Any]],
    limit: int = 20,
    seed: int = 42,
) -> list[TaskConfig]:
    pair_lookup = {
        frozenset({entry["drug1"], entry["drug2"]}): entry for entry in interaction_db
    }
    drug_to_neighbors: dict[str, set[str]] = defaultdict(set)
    for entry in interaction_db:
        drug_to_neighbors[entry["drug1"]].add(entry["drug2"])
        drug_to_neighbors[entry["drug2"]].add(entry["drug1"])

    rng = random.Random(seed)
    pair_pool = interaction_db[:]
    rng.shuffle(pair_pool)
    tasks: list[TaskConfig] = []
    seen_med_lists: set[tuple[str, ...]] = set()

    for anchor_index, anchor in enumerate(pair_pool):
        for partner in pair_pool[anchor_index + 1 :]:
            meds = {
                anchor["drug1"],
                anchor["drug2"],
                partner["drug1"],
                partner["drug2"],
            }
            if len(meds) < 4 or len(meds) > 5:
                continue

            filler_pool = [drug for drug in drug_to_neighbors if drug not in meds]
            rng.shuffle(filler_pool)
            while len(meds) < 5 and filler_pool:
                meds.add(filler_pool.pop())

            ordered_meds = tuple(sorted(meds))
            if ordered_meds in seen_med_lists:
                continue

            interactions = []
            for left_index, drug1 in enumerate(ordered_meds):
                for drug2 in ordered_meds[left_index + 1 :]:
                    match = pair_lookup.get(frozenset({drug1, drug2}))
                    if match is None:
                        continue
                    interactions.append(
                        {
                            "drug1": match["drug1"],
                            "drug2": match["drug2"],
                            "severity": match["severity"],
                            "mechanism": match["mechanism"],
                        }
                    )
            if len(interactions) < 2:
                continue

            seen_med_lists.add(ordered_meds)
            tasks.append(
                TaskConfig(
                    id=f"real-medium-{len(tasks) + 1:03d}",
                    task_type="medium",
                    prompt=(
                        "A patient is taking the following medications: "
                        + ", ".join(ordered_meds)
                        + ". Identify all clinically significant drug interactions and assign "
                        "a severity to each pair."
                    ),
                    input_data={"medications": list(ordered_meds)},
                    ground_truth={"interactions": interactions},
                    max_steps=1,
                    difficulty_score=0.55,
                )
            )
            if len(tasks) >= limit:
                return tasks

    return tasks
