"""
CardioAI — SQLite Database Helper
Handles persistent prediction history using a local SQLite file.
No external database server required — data persists in cardioai.db.
"""

import sqlite3
import os
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cardioai.db")

FEATURE_KEYS = [
    "age", "sex", "chest_pain_type", "resting_bp", "cholesterol",
    "fasting_blood_sugar", "resting_ecg", "max_heart_rate",
    "exercise_angina", "oldpeak", "st_slope",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_conn():
    """Get a new SQLite connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # better concurrent read performance
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_db():
    """Create the predictions table if it doesn't exist."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name        TEXT    NOT NULL,
            age                 REAL    NOT NULL,
            sex                 REAL    NOT NULL,
            chest_pain_type     REAL    NOT NULL,
            resting_bp          REAL    NOT NULL,
            cholesterol         REAL    NOT NULL,
            fasting_blood_sugar REAL    NOT NULL,
            resting_ecg         REAL    NOT NULL,
            max_heart_rate      REAL    NOT NULL,
            exercise_angina     REAL    NOT NULL,
            oldpeak             REAL    NOT NULL,
            st_slope            REAL    NOT NULL,
            prediction          TEXT    NOT NULL,
            probability         REAL    NOT NULL,
            confidence          REAL    NOT NULL,
            created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # Create indices for faster lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_patient_name ON predictions(patient_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON predictions(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prediction ON predictions(prediction)")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[DB] SQLite database ready at: {DB_PATH}")


# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

def save_prediction(patient_name: str, inputs: dict, result: dict) -> int:
    """Insert a prediction record. Returns the new row ID."""
    conn = _get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO predictions
                (patient_name, age, sex, chest_pain_type, resting_bp, cholesterol,
                 fasting_blood_sugar, resting_ecg, max_heart_rate, exercise_angina,
                 oldpeak, st_slope, prediction, probability, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_name,
                inputs["age"], inputs["sex"], inputs["chest_pain_type"],
                inputs["resting_bp"], inputs["cholesterol"],
                inputs["fasting_blood_sugar"], inputs["resting_ecg"],
                inputs["max_heart_rate"], inputs["exercise_angina"],
                inputs["oldpeak"], inputs["st_slope"],
                result["prediction"], result["probability"],
                result["confidence"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()


def get_predictions(
    page: int = 1,
    per_page: int = 15,
    search: str = "",
    date_from: str = "",
    date_to: str = "",
    sort_order: str = "desc",
) -> list[dict]:
    """
    Fetch paginated prediction records with optional filters.
    Excludes What-If analysis records (patient_name = '__whatif__').
    """
    conn = _get_conn()
    cursor = conn.cursor()

    where_clauses = ["patient_name != '__whatif__'"]
    params = []

    if search:
        where_clauses.append("patient_name LIKE ?")
        params.append(f"%{search}%")
    if date_from:
        where_clauses.append("created_at >= ?")
        params.append(f"{date_from} 00:00:00")
    if date_to:
        where_clauses.append("created_at <= ?")
        params.append(f"{date_to} 23:59:59")

    where_sql = "WHERE " + " AND ".join(where_clauses)

    order = "DESC" if sort_order.lower() == "desc" else "ASC"
    offset = (page - 1) * per_page

    query = f"""
        SELECT id, patient_name, age, sex, chest_pain_type, resting_bp,
               cholesterol, fasting_blood_sugar, resting_ecg, max_heart_rate,
               exercise_angina, oldpeak, st_slope, prediction, probability,
               confidence, created_at
        FROM predictions
        {where_sql}
        ORDER BY created_at {order}
        LIMIT ? OFFSET ?
    """
    params.extend([per_page, offset])

    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        # Convert sqlite3.Row objects to dicts
        return [dict(row) for row in rows]
    finally:
        cursor.close()
        conn.close()


def get_prediction_count(
    search: str = "",
    date_from: str = "",
    date_to: str = "",
) -> int:
    """Return total number of records matching the filters (excluding What-If)."""
    conn = _get_conn()
    cursor = conn.cursor()

    where_clauses = ["patient_name != '__whatif__'"]
    params = []

    if search:
        where_clauses.append("patient_name LIKE ?")
        params.append(f"%{search}%")
    if date_from:
        where_clauses.append("created_at >= ?")
        params.append(f"{date_from} 00:00:00")
    if date_to:
        where_clauses.append("created_at <= ?")
        params.append(f"{date_to} 23:59:59")

    where_sql = "WHERE " + " AND ".join(where_clauses)

    try:
        cursor.execute(f"SELECT COUNT(*) FROM predictions {where_sql}", params)
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()


def get_total_count() -> int:
    """Return total number of real prediction records (no filters, excludes What-If)."""
    conn = _get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM predictions WHERE patient_name != '__whatif__'")
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()
