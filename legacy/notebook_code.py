# Code cells of legacy/pynb_file.zip:pynb_file/car_emission_air_pollution.ipynb with outputs stripped.
# Extracted by `python -m nycemis legacy-audit`. Cell numbers are 0-based .ipynb indices.
# This file is evidence for docs/LEGACY_AUDIT.md; it is not meant to be run.

# %% [cell 2] execution_count=None
import traci
from sumolib import checkBinary

# Define the SUMO binary and configuration file path
sumoBinary = checkBinary('sumo-gui')
sumoConfig = r"D:\CodeBox\Data_Science\Air_Pollution\Project_Air_Pollution_Analysis_From_Car_Emission\flushing.sumocfg"

# Start the SUMO simulation
traci.start([sumoBinary, "-c", sumoConfig, "--start"])

# Run the simulation for 10-15 minutes (or 4000 simulation steps)
simulation_time = 4000  # in seconds
step = 0

# Define a list to store collected data
vehicle_data = []

while step < simulation_time:
    traci.simulationStep()  # Advance the simulation by one step
    
    # Get the list of all vehicle IDs in the simulation at the current step
    vehicle_ids = traci.vehicle.getIDList()
    
    # For each vehicle, collect emissions and positional data
    for vehicle_id in vehicle_ids:
        co2_emission = traci.vehicle.getCO2Emission(vehicle_id)  # CO2 emissions in mg
        speed = traci.vehicle.getSpeed(vehicle_id)               # Vehicle speed in m/s
        position = traci.vehicle.getPosition(vehicle_id)         # Vehicle position (x, y)
        
        # Append the collected data for this vehicle
        vehicle_data.append({
            "Step": step,
            "Vehicle_ID": vehicle_id,
            "CO2_Emission": co2_emission,
            "Speed": speed,
            "Position_X": position[0],
            "Position_Y": position[1]
        })
  
traci.close()

# %% [cell 4] execution_count=2
import pandas as pd

print("Display a sample of the collected data (first 5 entries)")
df = pd.DataFrame(vehicle_data)
df.head()

# %% [cell 6] execution_count=3
import pandas as pd
import xml.etree.ElementTree as ET


# Load emissions data
emissions_file = r'D:\CodeBox\Data_Science\Air_Pollution\Project_Air_Pollution_Analysis_From_Car_Emission\emissions_data.xml'
tree = ET.parse(emissions_file)
root = tree.getroot()

# Extract relevant data
data = []
for timestep in root.findall('timestep'):
    time = float(timestep.get('time'))
    for vehicle in timestep.findall('vehicle'):
        vehicle_id = vehicle.get('id')
        co2 = float(vehicle.get('CO2'))
        co = float(vehicle.get('CO'))
        nox = float(vehicle.get('NOx'))
        hc = float(vehicle.get('HC'))
        pmx = float(vehicle.get('PMx'))
        position_x = float(vehicle.get('x'))
        position_y = float(vehicle.get('y'))
        data.append([time, vehicle_id, co2, co, nox, hc, pmx, position_x, position_y])

# Create a DataFrame
df = pd.DataFrame(data, columns=['Time', 'Vehicle_ID', 'CO2', 'CO', 'NOx', 'HC', 'PMx', 'X', 'Y'])

# Show the original DataFrame and its row count
print("Original DataFrame:")
df.head()

row_count = len(df)
print(f'The DataFrame has {row_count} rows.\n')
df.head()

# %% [cell 8] execution_count=4
import pandas as pd

# Assuming df is your DataFrame that already contains CO2, CO, NOx, HC, PMx columns

# Calculate total emissions for each pollutant
total_co2 = df['CO2'].sum()
total_co = df['CO'].sum()
total_nox = df['NOx'].sum()
total_hc = df['HC'].sum()
total_pmx = df['PMx'].sum()

# Convert emissions data to percentages
df['CO2_Percentage'] = (df['CO2'] / total_co2) * 100
df['CO_Percentage'] = (df['CO'] / total_co) * 100
df['NOx_Percentage'] = (df['NOx'] / total_nox) * 100
df['HC_Percentage'] = (df['HC'] / total_hc) * 100
df['PMx_Percentage'] = (df['PMx'] / total_pmx) * 100

# Format the percentages to have '%' sign and limit decimal points to 2
df['CO2_Percentage'] = df['CO2_Percentage'].apply(lambda x: f"{x:.10f}%")
df['CO_Percentage'] = df['CO_Percentage'].apply(lambda x: f"{x:.10f}%")
df['NOx_Percentage'] = df['NOx_Percentage'].apply(lambda x: f"{x:.10f}%")
df['HC_Percentage'] = df['HC_Percentage'].apply(lambda x: f"{x:.10f}%")
df['PMx_Percentage'] = df['PMx_Percentage'].apply(lambda x: f"{x:.10f}%")

# Dynamically choose how many rows to display
def show_rows(num_rows):
    return df[['Time', 'Vehicle_ID', 'CO2_Percentage', 'CO_Percentage', 'NOx_Percentage', 'HC_Percentage', 'PMx_Percentage']].head(num_rows)


# Example usage:
num_rows = int(input("Enter how many rows you want to see: "))
print(f"\nDisplaying the first {num_rows} rows:")
show_rows(num_rows)

# %% [cell 10] execution_count=5
import numpy as np
# Check for empty (missing) cells
empty_cells = df.isnull().sum()

# Calculate entropy for numerical columns
def calculate_entropy(column):
    # Ignore NaN values for entropy calculation
    value_counts = column.value_counts()
    probabilities = value_counts / len(column.dropna())  # Drop NaN values for the calculation
    return -np.sum(probabilities * np.log(probabilities + 1e-9))  # Small constant to avoid log(0)

# Calculate entropy for each column
entropy_values = df.apply(calculate_entropy)

# Create a summary DataFrame for empty cells and entropy
summary_df = pd.DataFrame({
    'Empty Cells': empty_cells,
    'Entropy': entropy_values
})

# Reset index for better formatting
summary_df.reset_index(inplace=True)
summary_df.columns = ['Column', 'Empty Cells', 'Entropy']

# Print the summary DataFrame
print("Summary of Empty Cells and Entropy:")
summary_df

# %% [cell 12] execution_count=6
# Normalize the relevant columns (excluding Vehicle_ID)
normalized_df = df.copy()
columns_to_normalize = ['Time', 'CO2', 'CO', 'NOx', 'HC', 'PMx', 'X', 'Y']

# Min-Max normalization
normalized_df[columns_to_normalize] = normalized_df[columns_to_normalize].apply(lambda x: (x - x.min()) / (x.max() - x.min()))

# Display the normalized DataFrame
print("\nNormalized DataFrame:")
normalized_df.head()

# %% [cell 14] execution_count=7
import matplotlib.pyplot as plt
import seaborn as sns

# Set plot style
sns.set(style="whitegrid")

# Create a figure for the combined histogram
plt.figure(figsize=(10, 6))

# Plot histograms for each pollutant on the same plot
pollutants = ['CO2', 'CO', 'NOx', 'HC', 'PMx']
colors = ['g', 'b', 'r', 'c', 'm']
for pollutant, color in zip(pollutants, colors):
    sns.histplot(df[pollutant], bins=30, kde=True, color=color, label=pollutant, alpha=0.6)

# Add labels and title
plt.title('Combined Pollutant Levels Histogram')
plt.xlabel('Emission Levels')
plt.ylabel('Frequency')

# Add legend to differentiate pollutants
plt.legend(title="Pollutants")

# Show the plot
plt.tight_layout()
plt.show()

# %% [cell 16] execution_count=8
import matplotlib.pyplot as plt
import seaborn as sns

# Define pollutants to plot
pollutants = ['CO2', 'CO', 'NOx', 'HC', 'PMx']
colors = ['g', 'b', 'r', 'c', 'm']  

# Set plot style
sns.set(style="whitegrid")

# Loop through pollutants and create individual plots
for i, pollutant in enumerate(pollutants):
    plt.figure(figsize=(8, 6))  # Create a new figure for each plot with larger size
    sns.histplot(df[pollutant], bins=30, kde=True, color=colors[i])
    plt.title(f'{pollutant} Levels')
    plt.xlabel(f'{pollutant} Emissions')
    plt.ylabel('Frequency')
    
    plt.tight_layout()
    plt.show()


# import matplotlib.pyplot as plt
# import seaborn as sns
# 
# # Define pollutants to plot
# pollutants = ['CO2', 'CO', 'NOx', 'HC', 'PMx']
# colors = ['g', 'b', 'r', 'c', 'm']  
# 
# # Set plot style
# sns.set(style="whitegrid")
# 
# # Create a figure for all the subplots
# fig, axes = plt.subplots(1, 5, figsize=(20, 5))  # 1 row, 5 columns for each pollutant
# 
# # Plot histograms for each pollutant in the same figure
# for i, pollutant in enumerate(pollutants):
#     sns.histplot(df[pollutant], bins=30, kde=True, color=colors[i], ax=axes[i])  
#     axes[i].set_title(f'{pollutant} Levels')
#     axes[i].set_xlabel(f'{pollutant} Emissions')
#     axes[i].set_ylabel('Frequency')
# 
# # Adjust layout
# plt.tight_layout()
# plt.show()

# %% [cell 18] execution_count=9
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, ElasticNet
from sklearn.neighbors import KNeighborsRegressor
from sklearn.linear_model import Ridge
from xgboost import XGBRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error

# Split the data into features (X) and target (NOx) 
X = df[['CO2', 'CO', 'HC', 'PMx', 'X', 'Y']]  # Features (Pollutants and Position)
y = df['NOx']  # Target (NOx Emission levels)

# Split the dataset into 80% training and 20% testing
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Define the models
models = {
    "Random Forest": RandomForestRegressor(n_estimators=100, random_state=42),
    "XGBoost": XGBRegressor(n_estimators=100, random_state=42),
    "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
    "Linear Regression": LinearRegression(),
    "Ridge Regression": Ridge(alpha=1.0),
    "K-Nearest Neighbors": KNeighborsRegressor(),
    "Elastic Net": ElasticNet(),
    "Neural Network": MLPRegressor(hidden_layer_sizes=(100,), max_iter=1000, random_state=42)
}

# Initialize lists to store scores
train_scores = {}
test_scores = {}

# Train each model and calculate MSE
for name, model in models.items():
    # Fit the model
    model.fit(X_train, y_train)
    
    # Predictions for train and test
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)
    
    # Calculate MSE for train and test
    train_mse = mean_squared_error(y_train, y_train_pred)
    test_mse = mean_squared_error(y_test, y_test_pred)
    
    # Store the scores
    train_scores[name] = train_mse
    test_scores[name] = test_mse

# Create a DataFrame to display all models with their training and testing MSE
models_df = pd.DataFrame({
    'Model': list(train_scores.keys()),
    'Training MSE': list(train_scores.values()),
    'Testing MSE': list(test_scores.values())
})

# Sort models by testing MSE to find the best two
sorted_models = sorted(test_scores.items(), key=lambda x: x[1])
best_models = sorted_models[:2]  # Get the best two models

# Create a DataFrame for the best two models
best_models_df = pd.DataFrame(best_models, columns=['Model', 'Testing MSE'])

# Display the tables
print("\nAll Models - Training and Testing MSE:")
print(models_df)

print("\nBest Two Models Based on Testing MSE:")
best_models_df

# %% [cell 20] execution_count=10
# Plot time series chart for the two best models
best_model_names = [model[0] for model in best_models]
best_model_1 = models[best_model_names[0]]
best_model_2 = models[best_model_names[1]]

# Predictions for time series plot
y_test_pred_1 = best_model_1.predict(X_test)
y_test_pred_2 = best_model_2.predict(X_test)

# Time series plot
plt.figure(figsize=(10, 6))
plt.plot(y_test.values, label="Actual NOx", color='black', linewidth=2)
plt.plot(y_test_pred_1, label=f"{best_model_names[0]} Predicted NOx", linestyle='--')
plt.plot(y_test_pred_2, label=f"{best_model_names[1]} Predicted NOx", linestyle='--')

# Add titles and labels
plt.title("NOx Emission Levels: Actual vs Predicted")
plt.xlabel("Samples")
plt.ylabel("NOx Levels")
plt.legend()
plt.tight_layout()
plt.show()

# %% [cell 22] execution_count=12
import matplotlib.pyplot as plt
import seaborn as sns


# Convert your test_scores to a format suitable for plotting
model_names = list(test_scores.keys())
mse_values = list(test_scores.values())

# Set the color palette to darker pastel colors
colors = ['#4B8BBE', '#FF5C5C', '#B53C58', '#DAA520', '#4CA64C', '#D67F40', '#B0D3FF', '#FFC1A1']

# Set Seaborn style
sns.set(style="whitegrid")

# Create the bar plot using Seaborn
plt.figure(figsize=(10, 6))
sns.barplot(x=model_names, y=mse_values, hue=model_names, palette=colors, dodge=False, legend=False)

# Add value labels above each bar
for i, value in enumerate(mse_values):
    plt.text(i, value + 0.0001, round(value, 6), ha='center', color='black')

# Set plot title and labels
plt.title('Comparison of Model Performance (Testing MSE)', fontsize=16)
plt.xlabel('Models', fontsize=12)
plt.ylabel('Mean Squared Error (MSE)', fontsize=12)

# Show the plot
plt.tight_layout()
plt.show()

# %% [cell 24] execution_count=13
import pandas as pd
import numpy as np
import plotly.express as px

# Assuming we have time data for each timestep
timesteps = np.arange(1, 11)  

# Random Forest MSE values for each timestep (replace with actual MSE values)
random_forest_mse = [0.0001] * len(timesteps)

# XGBoost MSE values for each timestep (replace with actual MSE values)
xgboost_mse = [0.0005] * len(timesteps)

# Create a DataFrame for plotting
df_comparison = pd.DataFrame({
    'Timestep': timesteps,
    'Random Forest MSE': random_forest_mse,
    'XGBoost MSE': xgboost_mse
})

# Melt the DataFrame for easier plotting
df_melted = df_comparison.melt(id_vars='Timestep', 
                               value_vars=['Random Forest MSE', 'XGBoost MSE'],
                               var_name='Model', 
                               value_name='MSE')

# Plot using Plotly Express for time series comparison
fig = px.line(df_melted, 
              x='Timestep', 
              y='MSE', 
              color='Model',
              title='Random Forest vs XGBoost - Testing MSE over Time',
              labels={'Timestep': 'Time', 'MSE': 'Mean Squared Error'})

# Customize the plot appearance
fig.update_layout(
    plot_bgcolor='rgba(0, 0, 0, 0)',  # Transparent background
    paper_bgcolor='rgba(0, 0, 0, 0)',  # Transparent figure background
    font=dict(color='white'),
    title_font=dict(color='white')
)

# Show the plot
fig.show()

# %% [cell 26] execution_count=14
import plotly.graph_objects as go

# MSE values for the two models
model_names = ['Random Forest', 'XGBoost']
mse_values = [0.0001, 0.0005]  # Replace with actual MSE values

# Create a bar chart using Plotly
fig = go.Figure()

# Add bars for both models
fig.add_trace(go.Bar(
    x=model_names,
    y=mse_values,
    marker_color = ['#4B8BBE', '#FF5C5C'],  # Different colors for each model
    text=mse_values,
    textposition='auto'
))

# Customize layout
fig.update_layout(
    title={
        'text': "Random Forest vs XGBoost - Model Performance Comparison",
        'x': 0.5,
        'xanchor': 'center'
    },
    xaxis_title="Models",
    yaxis_title="Mean Squared Error (MSE)",
    plot_bgcolor='rgba(0, 0, 0, 0)',  # Transparent plot background
    paper_bgcolor='rgba(0, 0, 0, 0)',  # Transparent paper background
    font=dict(
        color='royalblue'  # Font color
    ),
    title_font=dict(
        color='royalblue'  # Title font color
    ),
    height=500,
    width=800
)

# Show the plot
fig.show()

# %% [cell 28] execution_count=15
import matplotlib.pyplot as plt

# Check if both datasets have valid data
if not df.empty:
    # Scatter plot of pollution levels before rerouting
    plt.figure(figsize=(10, 6))
    plt.scatter(df['X'], df['Y'], c=df['NOx'], cmap='Reds', s=50, alpha=0.5)
    plt.colorbar(label='NOx Levels)')
    plt.xlabel('X Position')
    plt.ylabel('Y Position')
    plt.title('Pollution Levels Before Model Application')
    plt.show()
else:
    print("No data available in df (before RFR Model)")

# %% [cell 30] execution_count=16
# Features and target
X = df[['CO2', 'CO', 'HC', 'PMx']]  # Only the pollution-related features for prediction
y = df['NOx']


# Train/Test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train the RandomForestRegressor
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)


# Evaluate the model
y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
print(f"Model Mean Squared Error: {mse}")

# %% [cell 32] execution_count=17
import numpy as np
from sklearn.metrics import confusion_matrix

# Define a threshold for NOx levels
threshold = 1.88  # 1.88 bpm for NYC

# Convert NOx levels to categorical (0 for low, 1 for high)
y_test_binned = np.where(y_test > threshold, 1, 0)
y_pred_binned = np.where(y_pred > threshold, 1, 0)

# Compute the confusion matrix
cm = confusion_matrix(y_test_binned, y_pred_binned)

# Function to plot confusion matrix with labels
def plot_confusion_matrix(cm, title, labels):
    plt.figure(figsize=(6, 4))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False, 
                xticklabels=labels, yticklabels=labels, annot_kws={"size": 14})
    plt.title(title)
    plt.ylabel('Actual')
    plt.xlabel('Predicted')
    plt.show()

# Labels for confusion matrix
labels = ['Low NOx', 'High NOx']

# Plotting the confusion matrix
plot_confusion_matrix(cm, 'Confusion Matrix - RandomForestRegressor', labels)

# %% [cell 34] execution_count=18
import matplotlib.pyplot as plt
import seaborn as sns

# Get predictions for the training set
y_train_pred = model.predict(X_train)

# Create a DataFrame for plotting train performance
train_df = pd.DataFrame({
    'Actual': y_train,
    'Predicted': y_train_pred
})

# Plot performance on the training set
plt.figure(figsize=(10, 6))
sns.lineplot(data=train_df, x=range(len(train_df)), y='Actual', label='Actual NOx', color='red')
sns.lineplot(data=train_df, x=range(len(train_df)), y='Predicted', label='Predicted NOx', color='blue')
plt.title('RandomForest Model Performance on Training Set')
plt.xlabel('Sample Index')
plt.ylabel('NOx Levels')
plt.legend()
plt.show()

# Create a DataFrame for plotting test performance
test_df = pd.DataFrame({
    'Actual': y_test,
    'Predicted': y_pred
})

# Plot performance on the test set
plt.figure(figsize=(10, 6))
sns.lineplot(data=test_df, x=range(len(test_df)), y='Actual', label='Actual NOx', color='red')
sns.lineplot(data=test_df, x=range(len(test_df)), y='Predicted', label='Predicted NOx', color='orange')
plt.title('RandomForest Model Performance on Test Set')
plt.xlabel('Sample Index')
plt.ylabel('NOx Levels')
plt.legend()
plt.show()

# %% [cell 36] execution_count=19
traci.close()

# %% [cell 37] execution_count=20
import traci
import pandas as pd
import warnings

# Suppress all warnings
warnings.filterwarnings("ignore")

# Initialize SUMO simulation
sumoConfig = r"D:\CodeBox\Data_Science\Air_Pollution\Project_Air_Pollution_Analysis_From_Car_Emission\flushing.sumocfg"
sumo_cmd = ["sumo-gui", "-c", sumoConfig, '--start']  # Update this path
traci.start(sumo_cmd)

pollution_threshold = 1.88 #######################################


def reroute_vehicle(vehicle_id):
    try:
        # Get current edge and vehicle's destination edge
        current_edge = traci.vehicle.getRoadID(vehicle_id)
        destination_edge = traci.vehicle.getRoute(vehicle_id)[-1]  # Last edge in the current route
        
        # Find an alternative route dynamically using SUMO's route finding function
        new_route = traci.simulation.findRoute(current_edge, destination_edge).edges
        
        if new_route and len(new_route) > 0:
            traci.vehicle.setRoute(vehicle_id, new_route)
            print(f"Vehicle {vehicle_id} rerouted to reduce pollution. New route: {new_route}")
        else:
            print(f"No valid alternative route found for vehicle {vehicle_id}.")
    
    except traci.TraCIException as e:
        print(f"Failed to reroute vehicle {vehicle_id}: {e}")

hotspot_data = []
step = 0

# Run the simulation until no more vehicles are active or max steps reached
while traci.simulation.getMinExpectedNumber() > 0 and step < 1000:
    traci.simulationStep()
    
    # For each vehicle, detect pollution levels
    for vehicle_id in traci.vehicle.getIDList():
        co2 = traci.vehicle.getCO2Emission(vehicle_id)
        co = traci.vehicle.getCOEmission(vehicle_id)
        hc = traci.vehicle.getHCEmission(vehicle_id)
        pmx = traci.vehicle.getPMxEmission(vehicle_id)

        # Create feature data with proper names
        feature_data = pd.DataFrame([[co2, co, hc, pmx]], columns=['CO2', 'CO', 'HC', 'PMx'])
        
        # Predict pollution level (NOx)
        predicted_nox = model.predict(feature_data)[0]
        
        if predicted_nox > pollution_threshold:
            print(f"High pollution detected for {vehicle_id} on edge {traci.vehicle.getRoadID(vehicle_id)}. Rerouting...")
            reroute_vehicle(vehicle_id)
        
        # Log hotspots
        position = traci.vehicle.getPosition(vehicle_id)
        hotspot_data.append([traci.simulation.getCurrentTime(), vehicle_id, predicted_nox, position])

    step += 1

traci.close()

# Convert logged data to DataFrame
df_hotspots = pd.DataFrame(hotspot_data, columns=['Time', 'Vehicle_ID', 'Predicted_NOx', 'Position'])

# Save the hotspot data
df_hotspots.to_csv('pollution_hotspots.csv', index=False)

# %% [cell 39] execution_count=22
# print(df_hotspots['Position'].head())

import pandas as pd
from IPython.display import display

df_head = df_hotspots[['Position']].head()
display(df_head)

# %% [cell 40] execution_count=23
# Ensure Position column contains tuples of (X, Y) coordinates
df_hotspots[['X', 'Y']] = pd.DataFrame(df_hotspots['Position'].tolist(), index=df_hotspots.index)


# Check if the splitting worked
df_hotspots[['X', 'Y']].head()

# %% [cell 41] execution_count=24
import matplotlib.pyplot as plt
import seaborn as sns

# Scatter plot for NOx levels based on vehicle positions (X, Y)
plt.figure(figsize=(10, 8))

# Create a scatter plot of the vehicles
scatter_plot = sns.scatterplot(
    data=df_hotspots,
    x='X',
    y='Y',
    hue='Predicted_NOx',  # Color intensity based on NOx levels
    palette='coolwarm',
    size='Predicted_NOx',  # Bubble size based on NOx levels
    sizes=(20, 200),  # Control min/max sizes
    legend='brief'
)

# Add plot titles and labels
plt.title('Vehicle Positions and Predicted NOx Levels After Rerouting')
plt.xlabel('X Coordinate (Longitude)')
plt.ylabel('Y Coordinate (Latitude)')
plt.legend(title='NOx Levels')
plt.colorbar(scatter_plot.collections[0], label='Predicted NOx (µg/m³)')

# Display the plot
plt.show()

# %% [cell 42] execution_count=25
import matplotlib.pyplot as plt
import seaborn as sns
import sumolib  # SUMO library to load network
import traci
import pandas as pd

# Load the SUMO network file (.net.xml)
net = sumolib.net.readNet(r'D:\CodeBox\Data_Science\Air_Pollution\Project_Air_Pollution_Analysis_From_Car_Emission\osm.view.xml')  # Update path to your .net.xml

# Create a plot to visualize the SUMO network
def plot_sumo_network(net, ax=None):
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 10))
    
    # Extract and plot edges from the SUMO network
    for edge in net.getEdges():
        shape = edge.getShape()
        x_coords = [p[0] for p in shape]
        y_coords = [p[1] for p in shape]
        ax.plot(x_coords, y_coords, color='gray', linewidth=1, alpha=0.6)
    
    return ax

# Plot the SUMO network
fig, ax = plt.subplots(figsize=(10, 10))
ax = plot_sumo_network(net, ax=ax)

# Ensure the NOx data has X and Y coordinates extracted from Position tuples
df_hotspots[['X', 'Y']] = pd.DataFrame(df_hotspots['Position'].tolist(), index=df_hotspots.index)

# Overlay NOx data on the SUMO map
sns.scatterplot(
    data=df_hotspots,
    x='X',
    y='Y',
    hue='Predicted_NOx',
    palette='coolwarm',
    size='Predicted_NOx',
    sizes=(20, 200),
    ax=ax,
    legend='brief'
)

# Customize and show the plot
plt.title('Predicted NOx Levels in SUMO Simulation After Rerouting')
plt.xlabel('X Coordinate')
plt.ylabel('Y Coordinate')
plt.colorbar(label='Predicted NOx (µg/m³)')
plt.show()

# %% [cell 45] execution_count=26
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import xml.etree.ElementTree as ET

# Assuming 'root' is your parsed XML ElementTree root
# Example: root = ET.parse('your_file.xml').getroot()

data = []
for timestep in root.findall('timestep'):
    time = float(timestep.get('time'))
    for vehicle in timestep.findall('vehicle'):
        vehicle_id = vehicle.get('id')
        co2 = float(vehicle.get('CO2'))
        co = float(vehicle.get('CO'))
        nox = float(vehicle.get('NOx'))
        hc = float(vehicle.get('HC'))
        pmx = float(vehicle.get('PMx'))
        position_x = float(vehicle.get('x'))
        position_y = float(vehicle.get('y'))
        data.append([time, vehicle_id, co2, co, nox, hc, pmx, position_x, position_y])

# Create a DataFrame
df = pd.DataFrame(data, columns=['Time', 'Vehicle_ID', 'CO2', 'CO', 'NOx', 'HC', 'PMx', 'X', 'Y'])

# Features and target (including vehicle position)
X = df[['CO2', 'CO', 'HC', 'PMx', 'X', 'Y']]  # Using CO2, CO, HC, PMx, and positions as features
y = df['NOx']  # Target is NOx

# Train/Test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Initialize the XGBoost Regressor
xgboost_model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, random_state=42)

# Train the model
xgboost_model.fit(X_train, y_train)

# Predict on the test set
y_pred = xgboost_model.predict(X_test)

# Evaluate the model using Mean Squared Error (MSE)
mse = mean_squared_error(y_test, y_pred)
print(f"XGBoost Model Mean Squared Error: {mse}")

# Save the model to a file
xgboost_model.save_model('xgboost_model.json')

# %% [cell 46] execution_count=28
import traci
import xgboost as xgb
import pandas as pd

# Initialize SUMO simulation
sumoConfig = r"D:\CodeBox\Data_Science\Air_Pollution\Project_Air_Pollution_Analysis_From_Car_Emission\flushing.sumocfg"
sumo_cmd = ["sumo-gui", "-c", sumoConfig, '--start']  # Update this path as needed
traci.start(sumo_cmd)

pollution_threshold = 1.88  # Set threshold based on NOx in ppm (1.88 for New York City)

# Load the pre-trained XGBoost model (assuming it is saved as 'xgboost_model.json')
xgboost_model = xgb.XGBRegressor()
xgboost_model.load_model("xgboost_model.json")  # Ensure the model is saved and loaded correctly
# Function to reroute the vehicle
def reroute_vehicle(vehicle_id):
    try:
        current_edge = traci.vehicle.getRoadID(vehicle_id)
        destination_edge = traci.vehicle.getRoute(vehicle_id)[-1]  # Get vehicle's destination
        
        # Find alternative route
        new_route = traci.simulation.findRoute(current_edge, destination_edge).edges
        
        if new_route:
            traci.vehicle.setRoute(vehicle_id, new_route)
            print(f"Vehicle {vehicle_id} rerouted. New route: {new_route}")
        else:
            print(f"No alternative route found for vehicle {vehicle_id}.")
    
    except traci.TraCIException as e:
        print(f"Error rerouting vehicle {vehicle_id}: {e}")

# Run the SUMO simulation
hotspot_data = []
step = 0

while traci.simulation.getMinExpectedNumber() > 0 and step < 1000:
    traci.simulationStep()
    
    # Check emissions for each vehicle in the simulation
    for vehicle_id in traci.vehicle.getIDList():
        co2 = traci.vehicle.getCO2Emission(vehicle_id)
        co = traci.vehicle.getCOEmission(vehicle_id)
        hc = traci.vehicle.getHCEmission(vehicle_id)
        pmx = traci.vehicle.getPMxEmission(vehicle_id)

        # Get the vehicle's position (X, Y)
        x_pos, y_pos = traci.vehicle.getPosition(vehicle_id)
    
        # Prepare features for NOx prediction
        feature_data = pd.DataFrame([[co2, co, hc, pmx, x_pos, y_pos]], columns=['CO2', 'CO', 'HC', 'PMx', 'X', 'Y'])
        
        # Predict NOx using the pre-trained XGBoost model
        predicted_nox = xgboost_model.predict(feature_data)[0]
    
        # Check if predicted NOx exceeds the pollution threshold
        if predicted_nox > pollution_threshold:
            print(f"High pollution detected for {vehicle_id} on edge {traci.vehicle.getRoadID(vehicle_id)}. Rerouting...")
            reroute_vehicle(vehicle_id)
    
        # Log hotspot data
        hotspot_data.append([traci.simulation.getCurrentTime(), vehicle_id, predicted_nox, (x_pos, y_pos)])

    # Increment simulation step
    step += 1

# Close the simulation
traci.close()

# Save the hotspot data to a CSV file
df_xbg = pd.DataFrame(hotspot_data, columns=['Time', 'Vehicle_ID', 'Predicted_NOx', 'Position'])
df_xbg.to_csv('pollution_hotspots_xgboost.csv', index=False)

# %% [cell 47] execution_count=35
print("Rerouting with XGBoost Model")
(df_xbg.head())

# %% [cell 48] execution_count=31
import matplotlib.pyplot as plt
import seaborn as sns
import sumolib

# Load the SUMO network file (.net.xml)
net = sumolib.net.readNet('D:\CodeBox\Data_Science\Air_Pollution\Project_Air_Pollution_Analysis_From_Car_Emission\osm.view.xml')  # Update path

# Create a plot to visualize the SUMO network
def plot_sumo_network(net, ax=None):
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 10))
    
    # Extract and plot edges from the SUMO network
    for edge in net.getEdges():
        shape = edge.getShape()
        x_coords = [p[0] for p in shape]
        y_coords = [p[1] for p in shape]
        ax.plot(x_coords, y_coords, color='gray', linewidth=1, alpha=0.6)
    
    return ax

# Plot the SUMO network
fig, ax = plt.subplots(figsize=(10, 10))
ax = plot_sumo_network(net, ax=ax)

# Ensure the NOx data has X and Y coordinates extracted from Position tuples
df_xbg[['X', 'Y']] = pd.DataFrame(df_xbg['Position'].tolist(), index=df_hotspots.index)

# Plot NOx levels as a scatter plot using plt.scatter (which supports color mapping)
sc = ax.scatter(
    df_xbg['X'],
    df_xbg['Y'],
    c=df_xbg['Predicted_NOx'],  # Set color based on NOx levels
    cmap='coolwarm',
    s=100,  # Marker size
    alpha=0.8
)

# Add colorbar for the scatter plot
cbar = plt.colorbar(sc, ax=ax)
cbar.set_label('Predicted NOx (µg/m³)')

# Customize and show the plot
plt.title('Predicted NOx Levels in SUMO Simulation After Rerouting (XGBoost)')
plt.xlabel('X Coordinate')
plt.ylabel('Y Coordinate')
plt.show()

# %% [cell 50] execution_count=36
import pandas as pd
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt

# Function to parse the XML file and extract emissions data
def parse_emissions_xml(file_path):
    data = []
    root = ET.parse(file_path).getroot()
    
    for timestep in root.findall('timestep'):
        for vehicle in timestep.findall('vehicle'):
            co2 = float(vehicle.get('CO2'))
            co = float(vehicle.get('CO'))
            nox = float(vehicle.get('NOx'))
            hc = float(vehicle.get('HC'))
            pmx = float(vehicle.get('PMx'))
            data.append([co2, co, nox, hc, pmx])
    
    return pd.DataFrame(data, columns=['CO2', 'CO', 'NOx', 'HC', 'PMx'])

# Parse the original emissions data
original_data = parse_emissions_xml('emissions_data.xml')

# Parse the model-generated emissions data
rf_data = parse_emissions_xml('emissions_data_rf.xml')
xbg_data = parse_emissions_xml('emissions_data_xgb.xml')

# Calculate total emissions for each dataset
original_totals = original_data.sum()
rf_totals = rf_data.sum()
xbg_totals = xbg_data.sum()

# Calculate the drop in emissions
drop_rf = original_totals - rf_totals
drop_xbg = original_totals - xbg_totals

# Calculate percentage drop in emissions
percentage_drop_rf = (drop_rf / original_totals) * 100
percentage_drop_xbg = (drop_xbg / original_totals) * 100

# Prepare a summary DataFrame for emission reductions
reduction_summary = pd.DataFrame({
    'Emission Type': original_totals.index,
    'Original Emissions': original_totals.values,
    'RF Emissions': rf_totals.values,
    'Drop (RF)': drop_rf.values,
    'Percentage Drop (RF)': percentage_drop_rf.values,
    'XGBoost Emissions': xbg_totals.values,
    'Drop (XGBoost)': drop_xbg.values,
    'Percentage Drop (XGBoost)': percentage_drop_xbg.values
})

# Display the summary DataFrame as a table
#print(reduction_summary)

# Optional: Display the summary DataFrame using pandas styling for better visualization
styled_summary = reduction_summary.style.set_table_attributes('style="width: 80%; margin: auto;"').set_caption("Emissions Reduction Summary")
styled_summary

# %% [cell 52] execution_count=37
import matplotlib.pyplot as plt
import seaborn as sns

# Function to parse the XML file and extract emissions data
def parse_emissions_xml(file_path):
    data = []
    root = ET.parse(file_path).getroot()
    
    for timestep in root.findall('timestep'):
        for vehicle in timestep.findall('vehicle'):
            co2 = float(vehicle.get('CO2'))
            co = float(vehicle.get('CO'))
            nox = float(vehicle.get('NOx'))
            hc = float(vehicle.get('HC'))
            pmx = float(vehicle.get('PMx'))
            data.append([co2, co, nox, hc, pmx])
    
    return pd.DataFrame(data, columns=['CO2', 'CO', 'NOx', 'HC', 'PMx'])

# Parse the original emissions data
original_data = parse_emissions_xml('emissions_data.xml')

# Parse the model-generated emissions data
rf_data = parse_emissions_xml('emissions_data_rf.xml')
xbg_data = parse_emissions_xml('emissions_data_xgb.xml')

# Set plot style
sns.set(style="whitegrid")

# Define pollutants to plot
pollutants = ['CO2', 'CO', 'NOx', 'HC', 'PMx']
colors = ['g', 'b', 'r']  # Original, RF, XGBoost colors

# Loop through pollutants and create individual plots
for i, pollutant in enumerate(pollutants):
    plt.figure(figsize=(10, 8))  # Create a new figure for each plot with larger size
    
    # Plot emissions histograms for each pollutant
    plt.hist(original_data[pollutant], bins=30, color='g', alpha=0.6, label='Original')
    plt.hist(rf_data[pollutant], bins=30, color='b', alpha=0.6, label='Random Forest')
    plt.hist(xbg_data[pollutant], bins=30, color='r', alpha=0.6, label='XGBoost')
    
    # Set titles and labels
    plt.title(f'{pollutant} Emissions Comparison')
    plt.xlabel(f'{pollutant} Emissions')
    plt.ylabel('Frequency')
    plt.legend()

    plt.tight_layout()
    plt.show()

# %% [cell 53] execution_count=38
import matplotlib.pyplot as plt
import seaborn as sns
import xml.etree.ElementTree as ET
import pandas as pd

# Function to parse the XML file and extract emissions data
def parse_emissions_xml(file_path):
    data = []
    root = ET.parse(file_path).getroot()
    
    for timestep in root.findall('timestep'):
        for vehicle in timestep.findall('vehicle'):
            co2 = float(vehicle.get('CO2'))
            co = float(vehicle.get('CO'))
            nox = float(vehicle.get('NOx'))
            hc = float(vehicle.get('HC'))
            pmx = float(vehicle.get('PMx'))
            data.append([co2, co, nox, hc, pmx])
    
    return pd.DataFrame(data, columns=['CO2', 'CO', 'NOx', 'HC', 'PMx'])

# Parse the original emissions data
original_data = parse_emissions_xml('emissions_data.xml')

# Parse the model-generated emissions data
rf_data = parse_emissions_xml('emissions_data_rf.xml')
xbg_data = parse_emissions_xml('emissions_data_xgb.xml')

# Define pollutants to plot
pollutants = ['CO2', 'CO', 'NOx', 'HC', 'PMx']

# Set plot style
sns.set(style="whitegrid")

# Loop through pollutants and create individual scatter plots
for pollutant in pollutants:
    plt.figure(figsize=(8, 6))  # Create a new figure for each plot with larger size
    
    # Scatter plot for Random Forest
    sns.scatterplot(x=original_data[pollutant], y=rf_data[pollutant], color='blue', alpha=0.6, label='RF Emissions')
    
    # Scatter plot for XGBoost
    sns.scatterplot(x=original_data[pollutant], y=xbg_data[pollutant], color='red', alpha=0.6, label='XGBoost Emissions')

    # Plot a diagonal reference line (Ideal case)
    plt.plot([original_data[pollutant].min(), original_data[pollutant].max()], 
             [original_data[pollutant].min(), original_data[pollutant].max()], 
             color='green', linestyle='--', label='Ideal') 

    # Set titles and labels
    plt.title(f'Original vs. RF & XGBoost - {pollutant}')
    plt.xlabel('Original Emissions')
    plt.ylabel('Model Emissions')

    # Add legend
    plt.legend()

    # Adjust layout and show the plot
    plt.tight_layout()
    plt.show()

# %% [cell 55] execution_count=39
import pandas as pd
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt

# Function to parse the XML file and extract emissions data
def parse_emissions_xml(file_path):
    data = []
    root = ET.parse(file_path).getroot()
    
    for timestep in root.findall('timestep'):
        for vehicle in timestep.findall('vehicle'):
            nox = float(vehicle.get('NOx'))
            data.append(nox)
    
    return pd.Series(data)

# Parse the original emissions data
original_nox = parse_emissions_xml('emissions_data.xml')

# Parse the model-generated emissions data
rf_nox = parse_emissions_xml('emissions_data_rf.xml')
xgb_nox = parse_emissions_xml('emissions_data_xgb.xml')

# Create a DataFrame to hold NOx data
nox_data = pd.DataFrame({
    'Original NOx': original_nox,
    'RF NOx': rf_nox,
    'XGBoost NOx': xgb_nox
})

# Create a line graph for NOx emissions
plt.figure(figsize=(12, 6))
plt.plot(nox_data.index, nox_data['Original NOx'], label='Original NOx', color='blue', linestyle='-', marker='o', markersize=2)
plt.plot(nox_data.index, nox_data['RF NOx'], label='Random Forest NOx', color='orange', linestyle='-', marker='o', markersize=2)
plt.plot(nox_data.index, nox_data['XGBoost NOx'], label='XGBoost NOx', color='green', linestyle='-', marker='o', markersize=2)

# Add titles and labels
plt.title('Comparison of NOx Emissions')
plt.xlabel('Time Step')
plt.ylabel('NOx Emissions')
plt.legend()
plt.grid()
plt.tight_layout()

# Show the plot
plt.show()

nox_data.head()

# %% [cell 57] execution_count=40
import folium
import pandas as pd

# Emissions data with actual NOx values and their percentages
data = {
    'Latitude': [40.7744, 40.7750, 40.7755],  # Slightly adjust latitudes for visual separation
    'Longitude': [-73.8265, -73.8260, -73.8255],  # Slightly adjust longitudes for visual separation
    'NOx_Emissions': [1.5, 2.3, 1.9],  # Sample NOx emissions values
    'Model': ['Original', 'Random Forest', 'XGBoost'],  # Labels for each model
    'Percentage Drop': [0, 15, 25]  # Example percentage drops, replace with actual values
}

# Create a DataFrame
nox_df = pd.DataFrame(data)

# Create a map centered around the specified location
flushing_map = folium.Map(location=[40.7744, -73.8265], zoom_start=13)

# Define a base radius for larger circles
base_radius = 1000  # Radius in meters for original emissions
rf_radius_factor = 1.5  # Factor to make the Random Forest circle larger
small_radius_factor = 0.5  # Factor to make smaller circles for XGBoost

# Add a marker for each NOx data point with circles
for _, row in nox_df.iterrows():
    # Big circle for original emissions
    if row['Model'] == 'Original':
        radius = base_radius  # Larger radius for original emissions
        outer_color = '#F32013'  # New color for Original outer circle
        inner_color = 'blue'  # Different color for the inner circle representing Original
    # Bigger circle for Random Forest
    elif row['Model'] == 'Random Forest':
        radius = base_radius * rf_radius_factor  # Increase radius for RF
        outer_color = 'purple'  # New color for Random Forest
        inner_color = 'purple'  # Keep inner circle the same color for clarity
    else:
        radius = base_radius * small_radius_factor  # Smaller radius for XGBoost
        outer_color = 'green'  # New color for XGBoost
        inner_color = 'green'  # Keep inner circle the same color for clarity

    # Create a larger circle for original emissions
    folium.Circle(
        location=(row['Latitude'], row['Longitude']),
        radius=radius,  # Adjust radius for original emissions
        color=outer_color,
        fill=True,
        fill_color=outer_color,
        fill_opacity=0.4,
        tooltip=f"{row['Model']} NOx: {row['NOx_Emissions']} ppm\nDrop: {row['Percentage Drop']}%"
    ).add_to(flushing_map)

    # Create a smaller circle for reduced emissions (XGBoost)
    if row['Model'] != 'Original':
        folium.Circle(
            location=(row['Latitude'], row['Longitude']),
            radius=radius * small_radius_factor,  # Smaller radius for XGBoost
            color=inner_color,
            fill=True,
            fill_color=inner_color,
            fill_opacity=0.6,
            tooltip=f"{row['Model']} NOx: {row['NOx_Emissions']} ppm\nDrop: {row['Percentage Drop']}%"
        ).add_to(flushing_map)

    # Add a label outside the circle
    folium.Marker(
        location=(row['Latitude'] + 0.0001, row['Longitude']),  # Adjusted slightly to place label outside
        icon=None,  # Use None to avoid default marker icon
        popup=f"{row['Model']} NOx: {row['NOx_Emissions']} ppm\nDrop: {row['Percentage Drop']}%",
        tooltip=f"{row['Model']} NOx: {row['NOx_Emissions']} ppm\nDrop: {row['Percentage Drop']}%"
    ).add_to(flushing_map)

# Save the map to an HTML file
flushing_map.save('flushing_nox_emissions_map.html')

# Display the map
flushing_map

# %% [cell 58] execution_count=None


