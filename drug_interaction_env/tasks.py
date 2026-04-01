from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Any


def normalize_drug_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


DRUG_INTERACTION_DB: list[dict[str, Any]] = [
    {
        "drug1": "warfarin",
        "drug2": "aspirin",
        "severity": "severe",
        "interaction_type": "pharmacodynamic",
        "mechanism": "additive anticoagulant effect",
        "keywords": ["bleeding", "anticoagulant", "hemorrhage"],
        "adverse_events": ["internal bleeding", "gi hemorrhage"],
        "clinical_outcome": "hospitalization",
    },
    {
        "drug1": "warfarin",
        "drug2": "fluconazole",
        "severity": "severe",
        "interaction_type": "pharmacokinetic",
        "mechanism": "cyp2c9 inhibition increases warfarin exposure and inr",
        "keywords": ["cyp2c9", "inr", "bleeding"],
        "adverse_events": ["supratherapeutic inr", "major bleeding"],
        "clinical_outcome": "hospitalization",
    },
    {
        "drug1": "simvastatin",
        "drug2": "clarithromycin",
        "severity": "severe",
        "interaction_type": "pharmacokinetic",
        "mechanism": "cyp3a4 inhibition increases statin concentration",
        "keywords": ["rhabdomyolysis", "cyp3a4", "myopathy"],
        "adverse_events": ["rhabdomyolysis", "acute kidney injury"],
        "clinical_outcome": "hospitalization",
    },
    {
        "drug1": "metformin",
        "drug2": "ibuprofen",
        "severity": "moderate",
        "interaction_type": "pharmacodynamic",
        "mechanism": "renal perfusion reduction may increase lactic acidosis risk",
        "keywords": ["renal", "lactic acidosis", "kidney"],
        "adverse_events": ["acute kidney injury", "lactic acidosis"],
        "clinical_outcome": "close monitoring",
    },
    {
        "drug1": "sertraline",
        "drug2": "tramadol",
        "severity": "severe",
        "interaction_type": "pharmacodynamic",
        "mechanism": "combined serotonergic activity can trigger serotonin syndrome",
        "keywords": ["serotonin syndrome", "agitation", "hyperreflexia"],
        "adverse_events": ["serotonin syndrome", "seizure"],
        "clinical_outcome": "emergency evaluation",
    },
    {
        "drug1": "lisinopril",
        "drug2": "potassium chloride",
        "severity": "moderate",
        "interaction_type": "pharmacodynamic",
        "mechanism": "reduced aldosterone effect increases potassium retention",
        "keywords": ["hyperkalemia", "potassium", "arrhythmia"],
        "adverse_events": ["hyperkalemia", "cardiac conduction changes"],
        "clinical_outcome": "lab monitoring",
    },
    {
        "drug1": "clopidogrel",
        "drug2": "omeprazole",
        "severity": "moderate",
        "interaction_type": "pharmacokinetic",
        "mechanism": "cyp2c19 inhibition reduces clopidogrel activation",
        "keywords": ["cyp2c19", "platelet", "reduced antiplatelet effect"],
        "adverse_events": ["stent thrombosis", "recurrent ischemia"],
        "clinical_outcome": "therapy adjustment",
    },
    {
        "drug1": "digoxin",
        "drug2": "amiodarone",
        "severity": "severe",
        "interaction_type": "pharmacokinetic",
        "mechanism": "p-glycoprotein inhibition increases digoxin levels",
        "keywords": ["toxicity", "arrhythmia", "digoxin"],
        "adverse_events": ["bradyarrhythmia", "visual changes"],
        "clinical_outcome": "hospitalization",
    },
    {
        "drug1": "methotrexate",
        "drug2": "ibuprofen",
        "severity": "severe",
        "interaction_type": "pharmacokinetic",
        "mechanism": "reduced renal clearance increases methotrexate exposure",
        "keywords": ["nephrotoxicity", "myelosuppression", "renal"],
        "adverse_events": ["bone marrow suppression", "acute kidney injury"],
        "clinical_outcome": "urgent medication review",
    },
    {
        "drug1": "sildenafil",
        "drug2": "nitroglycerin",
        "severity": "severe",
        "interaction_type": "pharmacodynamic",
        "mechanism": "combined vasodilation can cause profound hypotension",
        "keywords": ["hypotension", "syncope", "vasodilation"],
        "adverse_events": ["syncope", "shock"],
        "clinical_outcome": "emergency evaluation",
    },
    {
        "drug1": "phenelzine",
        "drug2": "fluoxetine",
        "severity": "severe",
        "interaction_type": "pharmacodynamic",
        "mechanism": "combined mao inhibition and serotonin reuptake blockade",
        "keywords": ["serotonin syndrome", "hypertension", "hyperthermia"],
        "adverse_events": ["serotonin syndrome", "hypertensive crisis"],
        "clinical_outcome": "emergency evaluation",
    },
    {
        "drug1": "ciprofloxacin",
        "drug2": "calcium carbonate",
        "severity": "mild",
        "interaction_type": "pharmacokinetic",
        "mechanism": "chelation reduces fluoroquinolone absorption",
        "keywords": ["chelation", "absorption", "reduced efficacy"],
        "adverse_events": ["treatment failure"],
        "clinical_outcome": "dose separation",
    },
    {
        "drug1": "amlodipine",
        "drug2": "simvastatin",
        "severity": "moderate",
        "interaction_type": "pharmacokinetic",
        "mechanism": "cyp3a4-mediated increase in simvastatin exposure",
        "keywords": ["cyp3a4", "myopathy", "statin"],
        "adverse_events": ["myalgia", "myopathy"],
        "clinical_outcome": "dose reduction",
    },
    {
        "drug1": "alcohol",
        "drug2": "metronidazole",
        "severity": "moderate",
        "interaction_type": "pharmacodynamic",
        "mechanism": "disulfiram-like reaction causes flushing and nausea",
        "keywords": ["disulfiram", "nausea", "vomiting"],
        "adverse_events": ["severe nausea", "vomiting"],
        "clinical_outcome": "avoidance counseling",
    },
    {
        "drug1": "lithium",
        "drug2": "ibuprofen",
        "severity": "severe",
        "interaction_type": "pharmacokinetic",
        "mechanism": "reduced renal clearance increases lithium concentration",
        "keywords": ["lithium toxicity", "tremor", "renal"],
        "adverse_events": ["confusion", "ataxia"],
        "clinical_outcome": "hospitalization",
    },
    {
        "drug1": "tacrolimus",
        "drug2": "fluconazole",
        "severity": "severe",
        "interaction_type": "pharmacokinetic",
        "mechanism": "cyp3a4 inhibition raises tacrolimus exposure",
        "keywords": ["nephrotoxicity", "cyp3a4", "tacrolimus"],
        "adverse_events": ["acute kidney injury", "tremor"],
        "clinical_outcome": "urgent dose adjustment",
    },
    {
        "drug1": "phenytoin",
        "drug2": "warfarin",
        "severity": "severe",
        "interaction_type": "pharmacokinetic",
        "mechanism": "protein binding displacement and cyp2c9 effects alter anticoagulation",
        "keywords": ["cyp2c9", "inr", "bleeding"],
        "adverse_events": ["bleeding", "loss of seizure control"],
        "clinical_outcome": "intensive monitoring",
    },
    {
        "drug1": "rifampin",
        "drug2": "ethinyl estradiol",
        "severity": "moderate",
        "interaction_type": "pharmacokinetic",
        "mechanism": "enzyme induction reduces oral contraceptive exposure",
        "keywords": ["cyp induction", "contraceptive failure", "reduced efficacy"],
        "adverse_events": ["breakthrough bleeding", "unintended pregnancy"],
        "clinical_outcome": "alternative contraception",
    },
    {
        "drug1": "codeine",
        "drug2": "diazepam",
        "severity": "severe",
        "interaction_type": "pharmacodynamic",
        "mechanism": "combined cns depressant effects impair respiration",
        "keywords": ["cns depression", "respiratory depression", "sedation"],
        "adverse_events": ["oversedation", "respiratory failure"],
        "clinical_outcome": "emergency evaluation",
    },
    {
        "drug1": "lisinopril",
        "drug2": "spironolactone",
        "severity": "moderate",
        "interaction_type": "pharmacodynamic",
        "mechanism": "combined raas blockade increases potassium retention",
        "keywords": ["hyperkalemia", "potassium", "ace inhibitor"],
        "adverse_events": ["hyperkalemia", "arrhythmia"],
        "clinical_outcome": "lab monitoring",
    },
    {
        "drug1": "trimethoprim-sulfamethoxazole",
        "drug2": "warfarin",
        "severity": "severe",
        "interaction_type": "pharmacokinetic",
        "mechanism": "cyp2c9 inhibition raises warfarin effect and inr",
        "keywords": ["cyp2c9", "inr", "bleeding"],
        "adverse_events": ["major bleeding", "supratherapeutic inr"],
        "clinical_outcome": "hospitalization",
    },
    {
        "drug1": "insulin",
        "drug2": "propranolol",
        "severity": "moderate",
        "interaction_type": "pharmacodynamic",
        "mechanism": "beta-blockade can mask adrenergic symptoms of hypoglycemia",
        "keywords": ["hypoglycemia", "masked symptoms", "beta blocker"],
        "adverse_events": ["severe hypoglycemia", "delayed recognition"],
        "clinical_outcome": "close monitoring",
    },
]

_PAIR_LOOKUP = {
    frozenset(
        {
            normalize_drug_name(entry["drug1"]),
            normalize_drug_name(entry["drug2"]),
        }
    ): entry
    for entry in DRUG_INTERACTION_DB
}


def lookup_pair(drug1: str, drug2: str) -> dict[str, Any]:
    key = frozenset({normalize_drug_name(drug1), normalize_drug_name(drug2)})
    entry = _PAIR_LOOKUP.get(key)
    if entry is None:
        raise KeyError(f"Unknown interaction pair: {drug1!r}, {drug2!r}")
    return entry


@dataclass
class TaskConfig:
    id: str
    task_type: str
    prompt: str
    input_data: dict[str, Any] = field(default_factory=dict)
    ground_truth: dict[str, Any] = field(default_factory=dict)
    max_steps: int = 1
    difficulty_score: float = 0.0


def _easy_task(task_id: str, drug1: str, drug2: str, context: str) -> TaskConfig:
    pair = lookup_pair(drug1, drug2)
    prompt = (
        f"{context} A patient is taking both {pair['drug1']} and {pair['drug2']}. "
        "What is the severity of the drug-drug interaction between these two medications? "
        "Provide a brief explanation of the mechanism."
    )
    return TaskConfig(
        id=task_id,
        task_type="easy",
        prompt=prompt,
        input_data={"drug1": pair["drug1"], "drug2": pair["drug2"]},
        ground_truth={
            "drug1": pair["drug1"],
            "drug2": pair["drug2"],
            "severity": pair["severity"],
            "interaction_type": pair["interaction_type"],
            "mechanism": pair["mechanism"],
            "required_keywords": list(pair["keywords"]),
            "adverse_events": list(pair["adverse_events"]),
            "clinical_outcome": pair["clinical_outcome"],
        },
        max_steps=1,
        difficulty_score=0.3,
    )


def _build_medium_ground_truth(pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
    interactions: list[dict[str, Any]] = []
    for drug1, drug2 in pairs:
        pair = lookup_pair(drug1, drug2)
        interactions.append(
            {
                "drug1": pair["drug1"],
                "drug2": pair["drug2"],
                "severity": pair["severity"],
                "mechanism": pair["mechanism"],
            }
        )
    return interactions


EASY_TASKS: list[TaskConfig] = [
    _easy_task("easy-warfarin-aspirin", "warfarin", "aspirin", ""),
    _easy_task("easy-warfarin-fluconazole", "warfarin", "fluconazole", ""),
    _easy_task("easy-simvastatin-clarithromycin", "simvastatin", "clarithromycin", ""),
    _easy_task("easy-sertraline-tramadol", "sertraline", "tramadol", ""),
    _easy_task("easy-lisinopril-potassium", "lisinopril", "potassium chloride", ""),
    _easy_task("easy-clopidogrel-omeprazole", "clopidogrel", "omeprazole", ""),
    _easy_task("easy-digoxin-amiodarone", "digoxin", "amiodarone", ""),
    _easy_task("easy-sildenafil-nitroglycerin", "sildenafil", "nitroglycerin", ""),
    _easy_task("easy-lithium-ibuprofen", "lithium", "ibuprofen", ""),
    _easy_task("easy-cipro-calcium", "ciprofloxacin", "calcium carbonate", ""),
    _easy_task("easy-codeine-diazepam", "codeine", "diazepam", ""),
    _easy_task("easy-rifampin-ocp", "rifampin", "ethinyl estradiol", ""),
]


MEDIUM_TASKS: list[TaskConfig] = [
    TaskConfig(
        id="medium-anticoag-polypharm",
        task_type="medium",
        prompt=(
            "A 65-year-old patient is taking warfarin, ibuprofen, omeprazole, aspirin, and metformin "
            "for atrial fibrillation, osteoarthritis, reflux, and diabetes. Identify all clinically "
            "significant drug interactions, listing each interacting pair and its severity level."
        ),
        input_data={
            "medications": ["warfarin", "ibuprofen", "omeprazole", "aspirin", "metformin"],
        },
        ground_truth={
            "interactions": _build_medium_ground_truth(
                [("warfarin", "aspirin"), ("metformin", "ibuprofen")]
            )
        },
        max_steps=1,
        difficulty_score=0.5,
    ),
    TaskConfig(
        id="medium-cardiology-meds",
        task_type="medium",
        prompt=(
            "A 72-year-old patient with heart failure is taking digoxin, amiodarone, lisinopril, "
            "spironolactone, and furosemide. Identify all clinically significant drug interactions and "
            "grade their severity."
        ),
        input_data={
            "medications": ["digoxin", "amiodarone", "lisinopril", "spironolactone", "furosemide"],
        },
        ground_truth={
            "interactions": _build_medium_ground_truth(
                [("digoxin", "amiodarone"), ("lisinopril", "spironolactone")]
            )
        },
        max_steps=1,
        difficulty_score=0.5,
    ),
    TaskConfig(
        id="medium-psych-pain",
        task_type="medium",
        prompt=(
            "A patient with depression and chronic pain is taking sertraline, tramadol, ibuprofen, "
            "lithium, and pantoprazole. Identify all clinically significant drug interactions, "
            "including the severity for each pair."
        ),
        input_data={
            "medications": ["sertraline", "tramadol", "ibuprofen", "lithium", "pantoprazole"],
        },
        ground_truth={
            "interactions": _build_medium_ground_truth(
                [("sertraline", "tramadol"), ("lithium", "ibuprofen")]
            )
        },
        max_steps=1,
        difficulty_score=0.5,
    ),
    TaskConfig(
        id="medium-transplant-infectious",
        task_type="medium",
        prompt=(
            "A kidney transplant recipient is taking tacrolimus, fluconazole, amlodipine, simvastatin, "
            "and calcium carbonate. Identify the clinically significant interactions and assign severity "
            "to each pair."
        ),
        input_data={
            "medications": ["tacrolimus", "fluconazole", "amlodipine", "simvastatin", "calcium carbonate"],
        },
        ground_truth={
            "interactions": _build_medium_ground_truth(
                [("tacrolimus", "fluconazole"), ("amlodipine", "simvastatin")]
            )
        },
        max_steps=1,
        difficulty_score=0.5,
    ),
    TaskConfig(
        id="medium-antibiotic-clinic",
        task_type="medium",
        prompt=(
            "A primary care patient is taking warfarin, trimethoprim-sulfamethoxazole, lisinopril, "
            "potassium chloride, and vitamin d. Identify all clinically significant drug interactions "
            "and their severities."
        ),
        input_data={
            "medications": [
                "warfarin",
                "trimethoprim-sulfamethoxazole",
                "lisinopril",
                "potassium chloride",
                "vitamin d",
            ],
        },
        ground_truth={
            "interactions": _build_medium_ground_truth(
                [("trimethoprim-sulfamethoxazole", "warfarin"), ("lisinopril", "potassium chloride")]
            )
        },
        max_steps=1,
        difficulty_score=0.5,
    ),
    TaskConfig(
        id="medium-respiratory-sedation",
        task_type="medium",
        prompt=(
            "A patient recovering from surgery is using codeine, diazepam, metronidazole, alcohol, and "
            "acetaminophen. Identify all clinically significant interactions and rate the severity."
        ),
        input_data={
            "medications": ["codeine", "diazepam", "metronidazole", "alcohol", "acetaminophen"],
        },
        ground_truth={
            "interactions": _build_medium_ground_truth(
                [("codeine", "diazepam"), ("alcohol", "metronidazole")]
            )
        },
        max_steps=1,
        difficulty_score=0.5,
    ),
]


HARD_TASKS: list[TaskConfig] = [
    TaskConfig(
        id="hard-bleeding-emergency",
        task_type="hard",
        prompt=(
            "A 74-year-old man with atrial fibrillation presents with melena, dizziness, and weakness. "
            "Vitals: BP 88/54, HR 118. Current medications: warfarin, aspirin, metformin, omeprazole. "
            "No known drug allergies. Determine the triage level, identify the most dangerous interaction, "
            "and recommend an immediate medication change with a brief explanation."
        ),
        input_data={
            "age": 74,
            "symptoms": ["melena", "dizziness", "weakness"],
            "vitals": {"bp": "88/54", "hr": 118},
            "medications": ["warfarin", "aspirin", "metformin", "omeprazole"],
            "allergies": [],
        },
        ground_truth={
            "triage": "emergency",
            "critical_interaction": {"drug1": "warfarin", "drug2": "aspirin", "severity": "severe"},
            "medication_change": "hold warfarin and aspirin immediately and evaluate for active bleeding",
            "target_drugs": ["warfarin", "aspirin"],
            "required_keywords": ["bleeding", "hemorrhage", "anticoagulant", "hypotension"],
        },
        max_steps=1,
        difficulty_score=0.9,
    ),
    TaskConfig(
        id="hard-serotonin-syndrome",
        task_type="hard",
        prompt=(
            "A 39-year-old woman arrives with agitation, diaphoresis, tremor, clonus, and a temperature "
            "of 39.2 C. Medications: sertraline for depression, tramadol started yesterday for pain, "
            "ondansetron as needed, and ibuprofen. BP 156/94, HR 126. No allergies. Determine the triage "
            "level, identify the critical interaction, and recommend medication changes."
        ),
        input_data={
            "age": 39,
            "symptoms": ["agitation", "diaphoresis", "tremor", "clonus", "fever"],
            "vitals": {"bp": "156/94", "hr": 126, "temp_c": 39.2},
            "medications": ["sertraline", "tramadol", "ondansetron", "ibuprofen"],
            "allergies": [],
        },
        ground_truth={
            "triage": "emergency",
            "critical_interaction": {"drug1": "sertraline", "drug2": "tramadol", "severity": "severe"},
            "medication_change": "stop tramadol and sertraline and evaluate for serotonin syndrome",
            "target_drugs": ["sertraline", "tramadol"],
            "required_keywords": ["serotonin syndrome", "clonus", "hyperthermia", "agitation"],
        },
        max_steps=1,
        difficulty_score=0.9,
    ),
    TaskConfig(
        id="hard-hyperkalemia",
        task_type="hard",
        prompt=(
            "A 67-year-old patient with hypertension and heart failure reports weakness and palpitations. "
            "Labs show potassium 6.1 mmol/L. Medications: lisinopril, spironolactone, potassium chloride, "
            "furosemide. BP 110/68, HR 98. Allergic to sulfa antibiotics. Determine the triage level, "
            "identify the key interaction, and advise medication changes."
        ),
        input_data={
            "age": 67,
            "symptoms": ["weakness", "palpitations"],
            "vitals": {"bp": "110/68", "hr": 98},
            "labs": {"potassium": 6.1},
            "medications": ["lisinopril", "spironolactone", "potassium chloride", "furosemide"],
            "allergies": ["sulfa antibiotics"],
        },
        ground_truth={
            "triage": "caution",
            "critical_interaction": {"drug1": "lisinopril", "drug2": "spironolactone", "severity": "moderate"},
            "medication_change": "stop potassium supplementation and reassess lisinopril plus spironolactone",
            "target_drugs": ["potassium chloride", "lisinopril", "spironolactone"],
            "required_keywords": ["hyperkalemia", "potassium", "arrhythmia", "ace inhibitor"],
        },
        max_steps=1,
        difficulty_score=0.9,
    ),
    TaskConfig(
        id="hard-rhabdo-risk",
        task_type="hard",
        prompt=(
            "A 58-year-old man being treated for pneumonia now has diffuse muscle pain and dark urine. "
            "Medications: simvastatin, clarithromycin started 3 days ago, amlodipine, metformin. "
            "Creatinine is rising from baseline. BP 124/76, HR 92. No allergies. Determine the triage "
            "level, identify the most important interaction, and recommend medication changes."
        ),
        input_data={
            "age": 58,
            "symptoms": ["myalgia", "dark urine"],
            "vitals": {"bp": "124/76", "hr": 92},
            "labs": {"creatinine_trend": "rising"},
            "medications": ["simvastatin", "clarithromycin", "amlodipine", "metformin"],
            "allergies": [],
        },
        ground_truth={
            "triage": "caution",
            "critical_interaction": {"drug1": "simvastatin", "drug2": "clarithromycin", "severity": "severe"},
            "medication_change": "stop simvastatin while clarithromycin is being used and assess for rhabdomyolysis",
            "target_drugs": ["simvastatin", "clarithromycin"],
            "required_keywords": ["rhabdomyolysis", "myopathy", "cyp3a4", "kidney"],
        },
        max_steps=1,
        difficulty_score=0.9,
    ),
]


class TaskLoader:
    DIFFICULTY_WEIGHTS = {"easy": 0.45, "medium": 0.35, "hard": 0.20}

    def __init__(self) -> None:
        self._by_id = {
            task.id: task for task in EASY_TASKS + MEDIUM_TASKS + HARD_TASKS
        }
        self._by_difficulty = {
            "easy": EASY_TASKS,
            "medium": MEDIUM_TASKS,
            "hard": HARD_TASKS,
        }

    def sample(self, rng: random.Random) -> TaskConfig:
        roll = rng.random()
        cumulative = 0.0
        selected = "hard"
        for difficulty, weight in self.DIFFICULTY_WEIGHTS.items():
            cumulative += weight
            if roll <= cumulative:
                selected = difficulty
                break
        return self.sample_by_difficulty(selected, rng)

    def get_by_id(self, task_id: str) -> TaskConfig:
        return self._by_id[task_id]

    def sample_by_difficulty(self, difficulty: str, rng: random.Random) -> TaskConfig:
        tasks = self._by_difficulty[difficulty]
        return tasks[rng.randrange(len(tasks))]
