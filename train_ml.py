import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# ==========================================
# 1. LOAD THE DATA
# ==========================================
personnel_df = pd.read_csv('personnel_dataset.csv')
workshops_df = pd.read_csv('training_workshops.csv')
historical_df = pd.read_csv('historical_allotments.csv')

# ==========================================
# 2. PREPARE TRAINING DATA (FEATURE ENGINEERING)
# ==========================================
# Merge historical data with personnel and workshop data to get a complete picture
merged_df = historical_df.merge(personnel_df, on='Personnel_ID').merge(workshops_df, on='Program_ID')

# Create our Features (X) and Labels (y)
def extract_features(df):
    features = pd.DataFrame()
    # Feature 1: How many trainings have they done? (Lower is better)
    features['Trainings_Completed'] = df['Trainings_Completed']
    
    # Feature 2: Performance Score (Higher is usually better for advanced courses)
    features['Performance_Score'] = df['Performance_Score']
    
    # Feature 3: Service Time Left
    features['Service_Time_Left'] = df['Service_Time_Left']
    
    # Feature 4: Does their Zone match the Target Zone of the workshop? (1 for Yes, 0 for No)
    features['Zone_Match'] = df.apply(
        lambda row: 1 if row['Target_Zone'] == 'All' or row['Target_Zone'] == row['Zone'] else 0, 
        axis=1
    )
    return features

X = extract_features(merged_df)
y = merged_df['Is_Optimal_Match']

# ==========================================
# 3. TRAIN THE RANDOM FOREST MODEL
# ==========================================
# Split data into training and testing sets (to evaluate performance)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Initialize the model (100 decision trees working together)
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)

# Train the model
rf_model.fit(X_train, y_train)

# (Optional) Evaluate the model
predictions = rf_model.predict(X_test)
print("--- Model Evaluation ---")
print(f"Accuracy: {accuracy_score(y_test, predictions) * 100:.2f}%")
print("------------------------\n")

# ==========================================
# 4. PREDICT & ALLOT FOR A NEW WORKSHOP
# ==========================================
def predict_best_candidates_optimized(program_id):
    # 1. Fetch target workshop
    workshop = workshops_df[workshops_df['Program_ID'] == program_id].iloc[0]
    
    # 2. Apply Hard Rules (Filter out retiring staff, match streams/levels)
    eligible = personnel_df[personnel_df['Service_Time_Left'] > 2.0].copy()
    eligible = eligible[eligible['Stream'] == workshop['Domain']]
    
    allowed_levels = workshop['Level_Of_Participants'].split('/')
    if 'All Officers' not in allowed_levels:
        eligible = eligible[eligible['Designation'].isin(allowed_levels)]
        
    # 3. Get the AI Probability Score for EVERYONE eligible
    eligible['Target_Zone'] = workshop['Target_Zone']
    X_new = extract_features(eligible)
    eligible['ML_Match_Probability'] = rf_model.predict_proba(X_new)[:, 1]
    
    # 4. THE LOGICAL COST-OPTIMIZATION FIX
    if workshop['Target_Zone'] != 'All':
        # Phase 1: Local Candidates First (Cost = Low)
        locals_df = eligible[eligible['Zone'] == workshop['Target_Zone']]
        locals_ranked = locals_df.sort_values(by='ML_Match_Probability', ascending=False)
        
        # Phase 2: Out-of-Zone Candidates (Cost = High)
        outsiders_df = eligible[eligible['Zone'] != workshop['Target_Zone']]
        outsiders_ranked = outsiders_df.sort_values(by='ML_Match_Probability', ascending=False)
        
        # Combine them: Locals are guaranteed to be placed at the top of the list
        final_ranking = pd.concat([locals_ranked, outsiders_ranked])
    else:
        # If the workshop is inherently a Pan-India ("All") workshop
        final_ranking = eligible.sort_values(by='ML_Match_Probability', ascending=False)
        
    # 5. Return only the top candidates up to the workshop's capacity
    return final_ranking.head(workshop['Capacity'])

# Run the Cost-Optimized AI Allotment
print(f"--- Cost-Optimized AI Results for D23EG03 (Target: North) ---")
best_candidates = predict_best_candidates_optimized('D23EG03')
print(best_candidates[['Personnel_ID', 'Name', 'Zone', 'Trainings_Completed', 'ML_Match_Probability']])