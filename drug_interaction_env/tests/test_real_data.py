from pathlib import Path

from scripts.real_data import (
    build_easy_eval_tasks,
    build_medium_eval_tasks,
    compile_interaction_db,
    discover_kagglehub_file,
    load_twosides_records,
    records_from_rows,
)


def test_load_twosides_records_and_compile_db(tmp_path: Path) -> None:
    csv_path = tmp_path / "twosides_sample.csv"
    csv_path.write_text(
        "\n".join(
            [
                "drug1,drug2,event_name,event_count",
                "warfarin,aspirin,GI hemorrhage,120",
                "warfarin,aspirin,internal bleeding,90",
                "sertraline,tramadol,serotonin syndrome,75",
                "lisinopril,potassium chloride,hyperkalemia,60",
            ]
        ),
        encoding="utf-8",
    )

    records = load_twosides_records(csv_path)
    compiled = compile_interaction_db(records, min_count=1)

    assert len(records) == 4
    assert compiled[0]["severity"] == "severe"
    assert compiled[0]["drug1"] == "aspirin"
    assert compiled[0]["drug2"] == "warfarin"
    assert "bleeding" in compiled[0]["keywords"] or "hemorrhage" in compiled[0]["keywords"]


def test_build_easy_and_medium_eval_tasks() -> None:
    compiled = [
        {
            "drug1": "aspirin",
            "drug2": "warfarin",
            "severity": "severe",
            "interaction_type": "dataset-derived",
            "mechanism": "dataset-derived safety signal centered on hemorrhage",
            "keywords": ["bleeding", "hemorrhage"],
            "adverse_events": ["internal bleeding"],
            "clinical_outcome": "hospitalization",
            "supporting_event_count": 120.0,
        },
        {
            "drug1": "sertraline",
            "drug2": "tramadol",
            "severity": "severe",
            "interaction_type": "dataset-derived",
            "mechanism": "dataset-derived safety signal centered on serotonin syndrome",
            "keywords": ["serotonin", "clonus"],
            "adverse_events": ["serotonin syndrome"],
            "clinical_outcome": "hospitalization",
            "supporting_event_count": 90.0,
        },
        {
            "drug1": "ibuprofen",
            "drug2": "lithium",
            "severity": "severe",
            "interaction_type": "dataset-derived",
            "mechanism": "dataset-derived safety signal centered on toxicity",
            "keywords": ["renal", "toxicity"],
            "adverse_events": ["lithium toxicity"],
            "clinical_outcome": "hospitalization",
            "supporting_event_count": 80.0,
        },
        {
            "drug1": "ibuprofen",
            "drug2": "metformin",
            "severity": "moderate",
            "interaction_type": "dataset-derived",
            "mechanism": "dataset-derived safety signal centered on kidney injury",
            "keywords": ["kidney", "renal"],
            "adverse_events": ["acute kidney injury"],
            "clinical_outcome": "close monitoring",
            "supporting_event_count": 70.0,
        },
    ]

    easy_tasks = build_easy_eval_tasks(compiled, limit=3)
    medium_tasks = build_medium_eval_tasks(compiled, limit=2, seed=7)

    assert len(easy_tasks) == 3
    assert easy_tasks[0].task_type == "easy"
    assert medium_tasks
    assert medium_tasks[0].task_type == "medium"
    assert len(medium_tasks[0].ground_truth["interactions"]) >= 2


def test_records_from_rows_parses_generic_tabular_input() -> None:
    rows = [
        {
            "drug_1": "Warfarin",
            "drug_2": "Aspirin",
            "side_effect_name": "GI hemorrhage",
            "count": "120",
        },
        {
            "drug_1": "Sertraline",
            "drug_2": "Tramadol",
            "side_effect_name": "Serotonin syndrome",
            "count": "75",
        },
    ]

    records = records_from_rows(rows)

    assert len(records) == 2
    assert records[0].drug1 == "warfarin"
    assert records[0].drug2 == "aspirin"
    assert records[0].event_name == "gi hemorrhage"


def test_discover_kagglehub_file_prefers_csv_and_relevant_name(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")
    (tmp_path / "other.parquet").write_text("x", encoding="utf-8")
    expected = tmp_path / "twosides_with_drug_names.csv"
    expected.write_text("drug1,drug2,event_name,count\n", encoding="utf-8")

    chosen = discover_kagglehub_file(tmp_path)

    assert chosen == str(expected)
