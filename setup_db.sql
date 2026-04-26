-- CardioAI Database Setup Script
-- Run this manually if the app cannot auto-create the database.

CREATE DATABASE IF NOT EXISTS cardioai
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE cardioai;

CREATE TABLE IF NOT EXISTS predictions (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    patient_name        VARCHAR(255)    NOT NULL,
    age                 FLOAT           NOT NULL,
    sex                 FLOAT           NOT NULL,
    chest_pain_type     FLOAT           NOT NULL,
    resting_bp          FLOAT           NOT NULL,
    cholesterol         FLOAT           NOT NULL,
    fasting_blood_sugar FLOAT           NOT NULL,
    resting_ecg         FLOAT           NOT NULL,
    max_heart_rate      FLOAT           NOT NULL,
    exercise_angina     FLOAT           NOT NULL,
    oldpeak             FLOAT           NOT NULL,
    st_slope            FLOAT           NOT NULL,
    prediction          VARCHAR(20)     NOT NULL,
    probability         FLOAT           NOT NULL,
    confidence          FLOAT           NOT NULL,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_patient_name (patient_name),
    INDEX idx_created_at   (created_at),
    INDEX idx_prediction   (prediction)
) ENGINE=InnoDB;
