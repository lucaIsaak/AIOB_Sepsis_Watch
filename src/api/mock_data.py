import math

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_UNITS = [
    "Medical Intensive Care Unit (MICU)",
    "Surgical Intensive Care Unit (SICU)",
    "Cardiac Vascular Intensive Care Unit (CVICU)",
    "Medical/Surgical Intensive Care Unit (MICU/SICU)",
    "Neuro Intermediate",
    "Trauma SICU (TSICU)",
    "Coronary Care Unit (CCU)",
]

_AGES = [28, 34, 41, 44, 47, 49, 52, 54, 56, 58, 61, 63, 65, 67, 68,
         70, 71, 72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 83, 84, 36]

_GENDERS = ["M", "F"]


def _attr(i: int, lst: list):
    """Deterministic cycle through a list."""
    return lst[i % len(lst)]


def _label(score: float) -> str:
    if score >= 0.8:
        return "CRITICAL"
    if score >= 0.6:
        return "HIGH"
    if score >= 0.4:
        return "MODERATE"
    return "LOW"


def _uncertainty(score: float, std: float) -> dict:
    flag = "HIGH" if std > 0.05 else ("MODERATE" if std > 0.03 else "LOW")
    return {
        "point_estimate": score,
        "variance": round(std ** 2, 5),
        "std": round(std, 4),
        "ci_lower": round(max(0.0, score - std), 4),
        "ci_upper": round(min(1.0, score + std), 4),
        "ci_width": round(2 * std, 4),
        "is_uncertain": std > 0.05,
        "uncertainty_flag": flag,
        "n_samples": 50,
    }


def _shap_top(score: float, age: float) -> list:
    s = score
    return [
        {"feature": "lactate_last",    "label": "Lactate (last 24h)",           "shap": round(s * 0.34, 3), "value": round(1.0 + s * 3.5, 1)},
        {"feature": "resp_rate_mean",  "label": "Respiratory Rate (mean)",      "shap": round(s * 0.30, 3), "value": round(14 + s * 16, 1)},
        {"feature": "gcs_motor",       "label": "GCS Motor Response",           "shap": round(s * 0.24, 3), "value": round(6 - s * 2, 1)},
        {"feature": "map_mean",        "label": "MAP (mean)",                   "shap": round(s * 0.21, 3), "value": round(90 - s * 35, 1)},
        {"feature": "wbc_last",        "label": "WBC Count (last)",             "shap": round(s * 0.19, 3), "value": round(8 + s * 12, 1)},
        {"feature": "spo2_min",        "label": "SpO2 (min)",                   "shap": round(s * 0.16, 3), "value": round(98 - s * 10, 1)},
        {"feature": "urine_out_24h",   "label": "Urine Output (24h)",           "shap": round(s * 0.15, 3), "value": round(1500 - s * 1200, 0)},
        {"feature": "creatinine_last", "label": "Creatinine (last)",            "shap": round(s * 0.14, 3), "value": round(0.9 + s * 2.2, 2)},
        {"feature": "hr_max",          "label": "Heart Rate (max)",             "shap": round(s * 0.12, 3), "value": round(75 + s * 55, 1)},
        {"feature": "bun_cr_ratio",    "label": "BUN / Creatinine Ratio",       "shap": round(s * 0.11, 3), "value": round(12 + s * 15, 1)},
        {"feature": "temp_last",       "label": "Temperature (°C, last)",       "shap": round(s * 0.10, 3), "value": round(37.0 + s * 2.2, 1)},
        {"feature": "platelet_last",   "label": "Platelet Count (last)",        "shap": round(s * 0.09, 3), "value": round(280 - s * 210, 0)},
        {"feature": "bilirubin_last",  "label": "Bilirubin (last)",             "shap": round(s * 0.08, 3), "value": round(0.5 + s * 3.2, 1)},
        {"feature": "anion_gap_last",  "label": "Anion Gap (last)",             "shap": round(s * 0.07, 3), "value": round(9 + s * 11, 1)},
        {"feature": "mech_vent_flag",  "label": "Mechanical Ventilation Flag",  "shap": round(s * 0.05, 3), "value": 1.0 if s > 0.6 else 0.0},
        {"feature": "age",             "label": "Age at Admission",             "shap": round(-s * 0.04, 3), "value": age},
    ]


_SHAP_BOTTOM = [
    {"feature": "sodium_last",      "label": "Sodium (last)",          "shap": -0.01, "value": 138.0},
    {"feature": "glucose_last",     "label": "Glucose (last)",         "shap":  0.02, "value": 128.0},
    {"feature": "sbp_min",          "label": "SBP (min)",              "shap": -0.02, "value": 92.0},
    {"feature": "dbp_mean",         "label": "DBP (mean)",             "shap":  0.01, "value": 55.0},
    {"feature": "fio2_mean",        "label": "FiO2 (mean)",            "shap":  0.02, "value": 0.40},
    {"feature": "peep_mean",        "label": "PEEP (mean)",            "shap":  0.01, "value": 6.0},
    {"feature": "los_pre_icu",      "label": "LOS before ICU (h)",     "shap": -0.01, "value": 10.0},
    {"feature": "icu_admit_source", "label": "ICU Admit Source",       "shap":  0.01, "value": 1.0},
]


# ---------------------------------------------------------------------------
# Generate 250 patients  (5 CRITICAL | 10 HIGH | 30 MODERATE | 205 LOW)
# ---------------------------------------------------------------------------

def _make_patients() -> list[dict]:
    groups = [
        # (count, score_min, score_max)
        (5,   0.80, 0.97),   # CRITICAL
        (10,  0.60, 0.79),   # HIGH
        (30,  0.40, 0.59),   # MODERATE
        (205, 0.03, 0.39),   # LOW
    ]
    patients = []
    idx = 0
    for count, lo, hi in groups:
        for k in range(count):
            # evenly spread scores within the band, add tiny variation via idx
            frac = k / max(count - 1, 1)
            score = round(hi - frac * (hi - lo), 4)
            # tiny zigzag so adjacent rows differ slightly
            score = round(score + (0.003 if idx % 2 == 0 else -0.003), 4)
            score = max(lo, min(hi, score))
            age = float(_attr(idx, _AGES))
            patients.append({
                "stay_id": 30010001 + idx,
                "risk_score": score,
                "risk_label": _label(score),
                "age": age,
                "first_careunit": _attr(idx, _UNITS),
                "gender": _attr(idx, _GENDERS),
            })
            idx += 1
    return patients


PATIENTS: list[dict] = _make_patients()

# ---------------------------------------------------------------------------
# Patient details (SHAP etc.) — generated on demand per patient
# ---------------------------------------------------------------------------

def _make_detail(p: dict, ood_flag: str = "NORMAL", outlier_features: list = None) -> dict:
    score = p["risk_score"]
    std = round(0.015 + score * 0.055, 4)
    return {
        **p,
        "shap_top": _shap_top(score, p["age"]),
        "shap_bottom": _SHAP_BOTTOM,
        "ood_flag": ood_flag,
        "outlier_features": outlier_features or [],
        "mahalanobis_distance": round(0.5 + score * 4.5, 2),
        "multivariate_novel": ood_flag != "NORMAL",
        "epistemic_uncertainty": _uncertainty(score, std),
    }


def _build_details() -> dict[int, dict]:
    details = {}
    for i, p in enumerate(PATIENTS):
        # First two CRITICAL patients get special treatment
        if i == 0:
            details[p["stay_id"]] = _make_detail(p, "CAUTION", ["Lactate (last 24h)", "Respiratory Rate (mean)"])
        else:
            details[p["stay_id"]] = _make_detail(p)
    return details


PATIENT_DETAILS: dict[int, dict] = _build_details()

# ---------------------------------------------------------------------------
# ROC curves
# ---------------------------------------------------------------------------

def _roc_curve(auroc: float, n: int = 50) -> list[dict]:
    pts = [{"fpr": 0.0, "tpr": 0.0}]
    for i in range(1, n):
        fpr = i / n
        tpr = min(1.0, 1.0 - math.pow(1.0 - fpr, 1.0 / (1.0 - auroc + 0.5)))
        pts.append({"fpr": round(fpr, 4), "tpr": round(tpr, 4)})
    pts.append({"fpr": 1.0, "tpr": 1.0})
    return pts


# ---------------------------------------------------------------------------
# Static data blobs
# ---------------------------------------------------------------------------

STATS = {
    "auroc": 0.8276,
    "news2_auroc": 0.606,
    "auprc": 0.353,
    "total_stays": 93224,
    "sepsis_cases": 9890,
    "features": 55,
    "roc_sepsis": _roc_curve(0.8276),
    "roc_news2": _roc_curve(0.606),
}

MODEL_INFO = {
    "algorithm": "GradientBoostingClassifier (sklearn 1.4.2)",
    "auroc": 0.8276,
    "auroc_ci_95": [0.818, 0.836],
    "news2_auroc_testset": 0.606,
    "auprc_testset": 0.3531,
    "brier_score": 0.0792,
    "feature_count": 55,
    "sklearn_version": "1.4.2",
    "training_data": "MIMIC-IV v3.1 — 93,224 ICU stays",
    "label_strategy": "Sepsis-3 ICD-10 proxy (A41.x / R65.2x)",
    "tuning": "Optuna Bayesian 50-trial search",
    "subgroup_auroc": {
        "male": 0.8305,
        "female": 0.8239,
        "age_young": 0.8352,
        "age_middle": 0.8277,
        "age_elderly": 0.8177,
    },
}

_n = len(PATIENTS)
_crit = sum(1 for p in PATIENTS if p["risk_label"] == "CRITICAL")
_high = sum(1 for p in PATIENTS if p["risk_label"] == "HIGH")
_mod  = sum(1 for p in PATIENTS if p["risk_label"] == "MODERATE")
_low  = sum(1 for p in PATIENTS if p["risk_label"] == "LOW")

DRIFT_STATUS = {
    "overall_status": "stable",
    "overall_psi": 0.04,
    "features": [
        {"feature": "resp_rate_mean",  "label": "Respiratory Rate (mean)", "train_mean": 18.4, "live_mean": 19.1, "psi": 0.03, "status": "stable"},
        {"feature": "hr_max",          "label": "Heart Rate (max)",        "train_mean": 86.2, "live_mean": 88.1, "psi": 0.02, "status": "stable"},
        {"feature": "lactate_last",    "label": "Lactate (last 24h)",      "train_mean": 2.1,  "live_mean": 2.8,  "psi": 0.12, "status": "moderate"},
        {"feature": "wbc_last",        "label": "WBC Count (last)",        "train_mean": 11.2, "live_mean": 11.8, "psi": 0.03, "status": "stable"},
        {"feature": "creatinine_last", "label": "Creatinine (last)",       "train_mean": 1.4,  "live_mean": 1.5,  "psi": 0.02, "status": "stable"},
        {"feature": "map_mean",        "label": "MAP (mean)",              "train_mean": 75.3, "live_mean": 74.8, "psi": 0.01, "status": "stable"},
    ],
    "risk_distribution": {
        "live": {
            "CRITICAL": round(_crit / _n, 3),
            "HIGH":     round(_high / _n, 3),
            "MODERATE": round(_mod  / _n, 3),
            "LOW":      round(_low  / _n, 3),
        },
        "expected": {"CRITICAL": 0.11, "HIGH": 0.18, "MODERATE": 0.35, "LOW": 0.36},
        "live_counts": {"CRITICAL": _crit, "HIGH": _high, "MODERATE": _mod, "LOW": _low},
        "total_live": _n,
    },
    "psi_history": [
        {"ts": "2025-05-13T08:00:00Z", "psi": 0.03, "status": "stable"},
        {"ts": "2025-05-14T08:00:00Z", "psi": 0.04, "status": "stable"},
        {"ts": "2025-05-15T08:00:00Z", "psi": 0.05, "status": "stable"},
        {"ts": "2025-05-16T08:00:00Z", "psi": 0.06, "status": "stable"},
        {"ts": "2025-05-17T08:00:00Z", "psi": 0.04, "status": "stable"},
    ],
    "evaluated_at": "2025-05-17T10:00:00Z",
    "live_patients": _n,
    "note": None,
}

FEEDBACK_AGENT_STATUS = {
    "decision": "WAIT",
    "reason": "Insufficient feedback volume — 0 clinical labels collected. Minimum 20 required before retraining is considered.",
    "evaluated_at": "2025-05-17T10:00:00Z",
    "clinical_total": 0,
    "confirmed_sepsis": 0,
    "flagged_wrong": 0,
    "fp_rate": None,
    "narrative_total": 0,
    "mean_rating": None,
    "std_rating": None,
    "low_rated_pct": None,
    "correction_notes": [],
    "details": {},
}

CLINICAL_NARRATIVE = """\
Patient stay {stay_id} — Risk Score: {score:.1%} ({label})

PRIMARY CONCERN: Elevated sepsis probability driven by multiple converging \
physiological markers consistent with early systemic inflammatory response and \
evolving organ dysfunction.

CLINICAL INDICATORS: Lactate trending at 3.8 mmol/L (critically elevated, \
+0.31 SHAP contribution), respiratory rate persistently elevated at 28 \
breaths/min (+0.28 SHAP), and GCS Motor Response deteriorating to 4/6 \
(+0.22 SHAP), consistent with early septic encephalopathy. Mean arterial \
pressure maintained at 62 mmHg through vasopressor support — borderline \
perfusion pressure requiring close titration.

CONTRIBUTING FACTORS: WBC count 18.2 × 10³/µL with left shift suggesting \
active bacterial infection. Urine output below 0.5 mL/kg/hr over the past \
6 hours. Creatinine rising from baseline to 2.4 mg/dL, suggesting acute \
kidney injury (KDIGO Stage 1–2). SpO2 dipping to 89% on current FiO2 \
settings.

RECOMMENDATION: This patient meets ≥2 organ dysfunction criteria under \
Sepsis-3 definition. Immediate senior physician review is recommended. \
Consider empiric broad-spectrum antibiotics pending blood culture results \
if not already initiated. Reassess fluid responsiveness (passive leg raise \
or pulse pressure variation) and vasopressor titration. Repeat lactate in \
2 hours to assess clearance trajectory.

[DEMO — This narrative is AI-generated and must be verified by a qualified \
clinician before any clinical decision.]"""
