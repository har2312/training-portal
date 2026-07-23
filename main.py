from fastapi import FastAPI, HTTPException
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from pydantic import BaseModel
import json

app = FastAPI(title="Training Allotment AI System")

# ==========================================
# 1. LOAD DATA & TRAIN MODEL ON STARTUP
# ==========================================
personnel_df = pd.read_csv('personnel_dataset.csv')
workshops_df = pd.read_csv('training_workshops.csv')
historical_df = pd.read_csv('historical_allotments.csv')

def extract_features(df):
    features = pd.DataFrame()
    features['Trainings_Completed'] = df['Trainings_Completed']
    features['Performance_Score'] = df['Performance_Score']
    features['Service_Time_Left'] = df['Service_Time_Left']
    features['Zone_Match'] = df.apply(
        lambda row: 1 if row['Target_Zone'] == 'All' or row['Target_Zone'] == row['Zone'] else 0, 
        axis=1
    )
    return features

# Train the model immediately when the server starts
merged_df = historical_df.merge(personnel_df, on='Personnel_ID').merge(workshops_df, on='Program_ID')
X = extract_features(merged_df)
y = merged_df['Is_Optimal_Match']

rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X, y)

# ==========================================
# 2. API ENDPOINTS
# ==========================================

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Training Allotment API"}

@app.get("/api/workshops")
def get_all_workshops():
    """Returns a list of all available training workshops."""
    # Convert dataframe to a dictionary format suitable for JSON
    return workshops_df.to_dict(orient="records")

@app.get("/api/allot/{program_id}")
def auto_allot_workshop(program_id: str):
    """Runs the AI and Business Logic to find the best candidates for a specific workshop."""
    
    # Check if workshop exists
    if program_id not in workshops_df['Program_ID'].values:
        raise HTTPException(status_code=404, detail="Workshop not found")
        
    workshop = workshops_df[workshops_df['Program_ID'] == program_id].iloc[0]
    
    # Apply Hard Rules
    eligible = personnel_df[personnel_df['Service_Time_Left'] > 2.0].copy()
    eligible = eligible[eligible['Stream'] == workshop['Domain']]
    
    allowed_levels = workshop['Level_Of_Participants'].split('/')
    if 'All Officers' not in allowed_levels:
        eligible = eligible[eligible['Designation'].isin(allowed_levels)]
        
    # Get ML Probabilities
    eligible['Target_Zone'] = workshop['Target_Zone']
    X_new = extract_features(eligible)
    eligible['ML_Match_Probability'] = rf_model.predict_proba(X_new)[:, 1]
    
    # Cost-Optimization (Local First)
    if workshop['Target_Zone'] != 'All':
        locals_df = eligible[eligible['Zone'] == workshop['Target_Zone']]
        locals_ranked = locals_df.sort_values(by='ML_Match_Probability', ascending=False)
        
        outsiders_df = eligible[eligible['Zone'] != workshop['Target_Zone']]
        outsiders_ranked = outsiders_df.sort_values(by='ML_Match_Probability', ascending=False)
        
        final_ranking = pd.concat([locals_ranked, outsiders_ranked])
    else:
        final_ranking = eligible.sort_values(by='ML_Match_Probability', ascending=False)
        
    # Get top candidates up to capacity
    best_candidates = final_ranking.head(workshop['Capacity'])
    
    # Select columns to send to the frontend dashboard
    output_columns = ['Personnel_ID', 'Name', 'Designation', 'Zone', 'Trainings_Completed', 'ML_Match_Probability']
    
    return {
        "program_id": program_id,
        "workshop_title": workshop['Title'],
        "capacity": int(workshop['Capacity']),
        "allotted_personnel": best_candidates[output_columns].to_dict(orient="records")
    }