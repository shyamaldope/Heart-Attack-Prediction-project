"""
AI-Powered Heart Attack Risk Prediction & Decision Support System
Flask backend with prediction API, feature importance, PDF reports,
and persistent SQLite-backed patient history.
"""

import pickle
import io
import math
import numpy as np
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from fpdf import FPDF
import db

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)

# Load pre-trained model and scaler
model = pickle.load(open("model.pkl", "rb"))
scaler = pickle.load(open("scaler (1).pkl", "rb"))

FEATURE_NAMES = [
    "Age", "Sex", "Chest Pain Type", "Resting BP", "Cholesterol",
    "Fasting Blood Sugar", "Resting ECG", "Max Heart Rate",
    "Exercise Angina", "Oldpeak", "ST Slope",
]

FEATURE_KEYS = [
    "age", "sex", "chest_pain_type", "resting_bp", "cholesterol",
    "fasting_blood_sugar", "resting_ecg", "max_heart_rate",
    "exercise_angina", "oldpeak", "st_slope",
]

# Initialise SQLite database on startup
db.init_db()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_feature_importance(features: list[float]) -> list[float]:
    """
    Perturbation-based local feature importance.
    For each feature, nudge it by ±10 % (min 0.5) and measure how the
    predicted probability of heart-attack risk changes.
    Works with any sklearn model (including StackingClassifier).
    """
    scaled = scaler.transform([features])
    base_prob = float(model.predict_proba(scaled)[0][1])

    importances = []
    for i in range(len(features)):
        perturbed = list(features)
        delta = max(abs(features[i] * 0.10), 0.5)
        perturbed[i] += delta
        p = float(model.predict_proba(scaler.transform([perturbed]))[0][1])
        importances.append(p - base_prob)

    return importances


def generate_recommendations(prediction: int, top_features: list[dict], inputs: dict) -> list[str]:
    """Return lifestyle recommendations based on prediction and key risk factors."""
    recs = []
    if prediction == 1:
        recs.append("⚠️ This patient is at HIGH RISK. Immediate clinical evaluation is recommended.")

        feature_set = {f["name"] for f in top_features}

        if "Cholesterol" in feature_set or inputs.get("cholesterol", 0) > 240:
            recs.append("• Implement a low-fat, plant-based diet to reduce cholesterol levels.")
        if "Resting BP" in feature_set or inputs.get("resting_bp", 0) > 140:
            recs.append("• Monitor and manage blood pressure with medication and lifestyle changes.")
        if "Max Heart Rate" in feature_set:
            recs.append("• Evaluate cardiac capacity; consider supervised exercise stress test.")
        if "Oldpeak" in feature_set or "ST Slope" in feature_set:
            recs.append("• ST segment abnormalities detected - consider echocardiography or angiography.")
        if "Fasting Blood Sugar" in feature_set or inputs.get("fasting_blood_sugar", 0) == 1:
            recs.append("• Control blood sugar through diet, exercise, and medication as needed.")
        if "Exercise Angina" in feature_set or inputs.get("exercise_angina", 0) == 1:
            recs.append("• Avoid strenuous activity until further cardiac evaluation is completed.")

        recs.append("• Encourage regular cardiovascular check-ups every 3-6 months.")
        recs.append("• Recommend smoking cessation and stress management programs.")
        recs.append("• Maintain a healthy BMI through balanced nutrition and moderate exercise.")
    else:
        recs.append("✅ This patient is at LOW RISK based on the current assessment.")
        recs.append("• Continue maintaining a healthy lifestyle with regular exercise.")
        recs.append("• Schedule annual cardiovascular screenings.")
        recs.append("• Monitor cholesterol and blood pressure periodically.")
    return recs


def pdf_safe(text):
    """Make text safe for fpdf2 built-in (latin-1) fonts."""
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2019": "'", "\u2018": "'",
        "\u201c": '"', "\u201d": '"', "\u2022": "-", "\u2026": "...",
        "\u00e2\u20ac\u201c": "-",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "ignore").decode("latin-1")


class ReportPDF(FPDF):
    """Custom PDF for the patient risk report."""

    def header(self):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(26, 35, 126)  # navy
        self.cell(0, 12, "Heart Attack Risk Assessment Report", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, "AI-Powered Clinical Decision Support System", new_x="LMARGIN", new_y="NEXT", align="C")
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(8)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(160, 160, 160)
        self.cell(0, 5, pdf_safe("This report is generated by an AI model and is intended to assist - not replace - clinical judgement."), new_x="LMARGIN", new_y="NEXT", align="C")
        self.cell(0, 5, pdf_safe(f"Page {self.page_no()}  |  Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"), new_x="LMARGIN", new_y="NEXT", align="C")

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    patient_name = data.get("patient_name", "Unknown Patient").strip()
    if not patient_name:
        patient_name = "Unknown Patient"

    features = [float(data[k]) for k in FEATURE_KEYS]

    # Predict
    scaled_input = scaler.transform([features])
    pred = int(model.predict(scaled_input)[0])
    proba = model.predict_proba(scaled_input)[0]
    risk_prob = float(proba[1])
    confidence = float(max(proba))

    # Feature importance
    importances = compute_feature_importance(features)
    indexed = sorted(
        enumerate(importances), key=lambda x: abs(x[1]), reverse=True
    )
    top_features = [
        {"name": FEATURE_NAMES[i], "importance": round(imp, 4)}
        for i, imp in indexed[:5]
    ]
    all_importances = [
        {"name": FEATURE_NAMES[i], "importance": round(importances[i], 4)}
        for i in range(len(FEATURE_NAMES))
    ]

    # Recommendations
    inputs_dict = dict(zip(FEATURE_KEYS, features))
    recommendations = generate_recommendations(pred, top_features, inputs_dict)

    result = {
        "prediction": "High Risk" if pred == 1 else "Low Risk",
        "probability": round(risk_prob, 4),
        "confidence": round(confidence, 4),
        "top_features": top_features,
        "all_importances": all_importances,
        "recommendations": recommendations,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Save to database (skip What-If analysis requests)
    if patient_name != "__whatif__":
        try:
            record_id = db.save_prediction(patient_name, inputs_dict, result)
            result["record_id"] = record_id
            result["patient_name"] = patient_name
        except Exception as e:
            print(f"[DB] Failed to save prediction: {e}")

    return jsonify(result)


@app.route("/history")
def history():
    """
    Paginated, filterable prediction history.
    Query params: page, per_page, search, date_from, date_to, sort
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 15, type=int)
    search = request.args.get("search", "", type=str).strip()
    date_from = request.args.get("date_from", "", type=str).strip()
    date_to = request.args.get("date_to", "", type=str).strip()
    sort_order = request.args.get("sort", "desc", type=str).strip()

    # Clamp per_page
    per_page = max(5, min(per_page, 100))

    try:
        records = db.get_predictions(
            page=page,
            per_page=per_page,
            search=search,
            date_from=date_from,
            date_to=date_to,
            sort_order=sort_order,
        )
        total = db.get_prediction_count(
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
        total_pages = max(1, math.ceil(total / per_page))

        return jsonify({
            "records": records,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        })
    except Exception as e:
        print(f"[DB] History query failed: {e}")
        return jsonify({"records": [], "total": 0, "page": 1, "per_page": per_page, "total_pages": 1})


@app.route("/history/stats")
def history_stats():
    """Return total record count for the dashboard card."""
    try:
        total = db.get_total_count()
        return jsonify({"total": total})
    except Exception as e:
        print(f"[DB] Stats query failed: {e}")
        return jsonify({"total": 0})


@app.route("/report", methods=["POST"])
def report():
    """Generate a downloadable PDF risk report."""
    data = request.json
    inputs = data.get("inputs", {})
    result = data.get("result", {})

    pdf = ReportPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=25)

    # --- Patient Details ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(33, 33, 33)
    pdf.cell(0, 10, "Patient Details", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)

    # Patient name
    patient_name = data.get("patient_name", "N/A")
    pdf.cell(60, 7, "Patient Name:", new_x="RIGHT")
    pdf.cell(0, 7, str(patient_name), new_x="LMARGIN", new_y="NEXT")

    labels_map = dict(zip(FEATURE_KEYS, FEATURE_NAMES))
    for key in FEATURE_KEYS:
        val = inputs.get(key, "N/A")
        pdf.cell(60, 7, f"{labels_map[key]}:", new_x="RIGHT")
        pdf.cell(0, 7, str(val), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # --- Risk Assessment ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(33, 33, 33)
    pdf.cell(0, 10, "Risk Assessment", new_x="LMARGIN", new_y="NEXT")

    pred_text = result.get("prediction", "N/A")
    prob = result.get("probability", 0)
    conf = result.get("confidence", 0)

    if pred_text == "High Risk":
        pdf.set_text_color(211, 47, 47)
    else:
        pdf.set_text_color(56, 142, 60)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"Result: {pred_text}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(60, 60, 60)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Risk Probability: {prob * 100:.1f}%", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Model Confidence: {conf * 100:.1f}%", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # --- Top Contributing Factors ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(33, 33, 33)
    pdf.cell(0, 10, "Top Contributing Factors", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    for feat in result.get("top_features", []):
        direction = "increases" if feat["importance"] > 0 else "decreases"
        pdf.cell(0, 7, f"  - {feat['name']} - {direction} risk by {abs(feat['importance']) * 100:.1f}%", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # --- Recommendations ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(33, 33, 33)
    pdf.cell(0, 10, "Recommendations", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    for rec in result.get("recommendations", []):
        clean = pdf_safe(rec).strip()
        if clean:
            pdf.set_x(10)
            pdf.multi_cell(w=190, h=7, text=f"  {clean}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # --- Model Info ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(33, 33, 33)
    pdf.cell(0, 10, "Model Information", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    for line in [
        "Algorithm: Stacking Ensemble Classifier",
        "Accuracy: 93.7%",
        "ROC-AUC: 0.97",
        "F1 Score: 0.94",
        "Cross-Validation: 91.65%",
    ]:
        pdf.cell(0, 7, f"  {line}", new_x="LMARGIN", new_y="NEXT")

    # Output to temp file (more reliable than BytesIO with fpdf2)
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_path = tmp.name
    tmp.close()
    pdf.output(tmp_path)
    response = send_file(
        tmp_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Heart_Risk_Report.pdf",
    )
    # Clean up after response is sent
    @response.call_on_close
    def cleanup():
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5000)
