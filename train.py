import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# 1. Load Data
personnel = pd.read_csv('personnel_dataset.csv')
workshops = pd.read_csv('training_workshops.csv')
historical = pd.read_csv('historical_allotments.csv')

def get_smart_allotments(program_id):
    # Fetch target workshop details
    workshop = workshops[workshops['Program_ID'] == program_id].iloc[0]
    
    # RULE 1: Hard filter out anyone retiring soon (Service_Time_Left <= 2 years)
    eligible = personnel[personnel['Service_Time_Left'] > 2.0].copy()
    
    # RULE 2: Stream Matching (Engineering workshop needs Engineering staff)
    eligible = eligible[eligible['Stream'] == workshop['Domain']]
    
    # RULE 3: Level/Designation Matching
    allowed_levels = workshop['Level_Of_Participants'].split('/')
    if 'All Officers' not in allowed_levels:
        eligible = eligible[eligible['Designation'].isin(allowed_levels)]
        
    # ML FEATURE ENGINEERING: Calculate a synthetic suitability score or rank candidates
    # Lower 'Trainings_Completed' = Higher priority
    # Higher 'Performance_Score' = Better fit for advanced leadership workshops
    
    # You can train a model using your historical data:
    # X = historical features, y = Is_Optimal_Match
    # model.predict_proba(current_eligible_pool)
    
    # Simple mathematical ranking simulation before ML model inference:
    eligible['Suitability_Weight'] = (10 - eligible['Trainings_Completed']) * 1.5 + (eligible['Performance_Score'] * 0.5)
    
    # Sort candidates by Zone first (if applicable), then by ML suitability weight
    if workshop['Target_Zone'] != 'All':
        # Push matching zone to top
        eligible['Zone_Match'] = eligible['Zone'] == workshop['Target_Zone']
        eligible = eligible.sort_values(by=['Zone_Match', 'Suitability_Weight'], ascending=[False, False])
    else:
        eligible = eligible.sort_values(by='Suitability_Weight', ascending=False)
        
    return eligible.head(workshop['Capacity'])

# Example Run for the IP-Based Studio Workshop
print(get_smart_allotments('D23EG03')[['Personnel_ID', 'Name', 'Zone', 'Trainings_Completed', 'Service_Time_Left']])