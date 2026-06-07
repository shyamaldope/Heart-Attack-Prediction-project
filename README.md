# CardioGuard — Heart Attack Risk Prediction

## Overview
A clinical decision support tool that predicts heart attack risk 
using a Stacking Ensemble ML model achieving 93.7% accuracy 
and 0.97 ROC-AUC on 1,190 UCI patient records.

## Tech Stack
Python, Scikit-learn, XGBoost, SHAP, Streamlit

## Features
- Stacking Ensemble (Random Forest + XGBoost + Gradient Boosting)
- SMOTE class balancing for imbalanced data
- SHAP explainability for transparent predictions
- Risk scoring: Low (<30%), Medium (30-60%), High (≥60%)
- What-If lifestyle simulation
- PDF report generation

## Dataset
UCI Heart Disease Dataset — 1,190 patient records 
from 5 global clinical sources

## Results
- Accuracy: 93.7%
- ROC-AUC: 0.97

## How to Run
1. Clone the repo
2. pip install -r requirements.txt
3. streamlit run app.py
