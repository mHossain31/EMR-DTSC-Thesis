# Text of SUMO_ML_Project.pdf (31 PDF pages, pypdf layout extraction)

## PDF page 1

Real-Time Emission
Reduction in Urban Traffic
Using Machine Learning
College of Engineering & Technology
NYIT

## PDF page 2

TABLE OF CONTENTS
01 Problem Statement
Global Vehicular Emissions
02 Experimentation
Our Approach Towards Environmental Sustainability
03 Analysis & Discussion
Effectiveness of Our Research

## PDF page 3

01
Problem
Statement

## PDF page 4

Addressing Urban Air Quality
Challenge
Urbanization has led to a surge in vehicle Traditional methods of trafﬁc control and
trafﬁc, which signiﬁcantly contributes to air emission reduction are often static and fail
pollution, particularly in metropolitan areas. to adapt in real-time to ﬂuctuating trafﬁc
Emissions from cars, trucks, and buses volumes and environmental conditions.
release harmful pollutants like nitrogen Densely populated areas demand dynamic
oxides (NOx), particulate matter (PM), and solutions that can respond promptly to
carbon monoxide (CO), deteriorating air changes, identifying pollution spikes as
quality and impacting public health. they occur and addressing them through
effective strategies such as predictive
trafﬁc rerouting.

## PDF page 5

Traffic Emissions: A Growing Urban Challenge

## PDF page 6

Focus on
Flushing, NYC
A Case Study in Dense Urban
Pollution
Urban Challenges in Flushing: Why Flushing?
● Flushing serves as an ideal ● This neighborhood represents
test location for studying many common emission issues
urban emissions due to its faced by urban centers
high population density and worldwide, making ﬁndings
environmental challenges. applicable on a global scale.

## PDF page 7

Existing Traffic & Emission
Control Approaches
Jiang et al. Lin et al. Dong & Javid etal.
(2022) (2020) (2022)
Focus: Extensive review of Focus: Integration of SUMO Focus: Reinforcement
ML models for air pollution with real-world trafﬁc data learning for dynamic vehicle
prediction, particularly to generate reliable re-routing and optimization
regression and neural emissions data from taxi of trafﬁc signals.
networks. trajectories.
Findings: Showed a
Findings: Highlighted ML's Findings: Improved spatial reduction in pollutant levels
effectiveness in capturing and temporal accuracy in by up to 20% through trafﬁc
complex relationships modeling pollution ﬂow adjustments.
between pollutants like CO2 hotspots.
and NOx with trafﬁc data.

## PDF page 8

Data-Driven, Dynamic Solution
ML-Powered Trafﬁc Congestion Detection
● Machine learning models are trained to monitor and analyze trafﬁc patterns
in real time, accurately identifying congestion hotspots to enable prompt
and effective interventions
Dynamic Rerouting to Improve Flow & Reduce Emissions
● Vehicles are rerouted around congested areas to prevent bottlenecks,
reduce idling, and lower emission levels

## PDF page 9

Simulation of
Urban MObility
SUMO is an open-source, highly
customizable trafﬁc simulation platform
that is integral to our research. Designed to
model the complex dynamics of trafﬁc in
urban settings, SUMO provides the tools
necessary to simulate real-world trafﬁc
conditions and analyze the impact of
various interventions on congestion and
emissions.

## PDF page 10

OpenStreetMap
(OSM)
SUMO’s OSM Web Wizard tool allows us to
generate a detailed simulation map of the
Flushing neighborhood in Queens, NYC. This
map replicates the real-world road
network and trafﬁc conditions, making it
an ideal setting for our congestion and
pollution reduction experiments.

## PDF page 11

02
Experimentation

## PDF page 12

Flow Chart
End-to-End Workﬂow
● From setting up a simulation
environment with SUMO and
generating data to training multiple
ML models for air pollution
prediction and selecting
top-performing models.
Real-Time Application & Analysis
● Implementing dynamic vehicle
re-routing to reduce emissions in
real-time, followed by performance
analysis to assess overall impact on
air quality.

## PDF page 13

Data Collection & Processing
Initial Dataset Generation
● Emissions data (CO2, CO, NOx, HC, PMx) and
positional coordinates for each vehicle are
saved in an emissions.xml ﬁle. This provides
the raw data essential for model training.
Data Conversion
● Post-simulation, the raw XML data is parsed
and converted into a structured Pandas
DataFrame (as shown on the right). This
format is suitable for further processing and
is then used to train and test our machine
learning models.

## PDF page 14

ML Model Selection
Objective
Implement various machine learning models
on our initial dataset to evaluate their
effectiveness in detecting and predicting air
pollution hotspots.
Model Comparison
Each model was tested for its ability to
predict pollution levels and identify
high-emission zones. Through this process,
we analyzed each model’s performance using
Mean Squared Error (MSE) as the key metric.
Based on performance outcomes, the Random Forest Regressor and XGBoost models demonstrated the lowest
MSE, making them the optimal choices for further development.

## PDF page 15

Random Forest Model
Model Overview Real-Time
The Random Forest Regressor, Integration
a robust ensemble learning The model was implemented within
algorithm, was selected due to our dynamic vehicle re-routing
its effectiveness in handling algorithm in SUMO, allowing it to
complex, non-linear data like identify high-emission areas in
real-time trafﬁc and pollution real-time and adjust trafﬁc ﬂow to
patterns. mitigate pollution.
Training Goal
We trained this model on Dynamically rerouting vehicles
historical emission data, in detected hotspot zones,
allowing it to recognize model aims to lower emission
patterns and predict potential levels / prevent congestion
pollution hotspots with high buildup, contributing to air
accuracy. quality improvement.

## PDF page 16

XGBoosting
Extreme Gradient Boosting, is an advanced tree-based
machine learning model known for its speed and
predictive accuracy, especially useful in handling large
datasets with complex patterns.
In this experiment, XGBoost’s strength in capturing subtle
relationships within the data made it ideal for predicting
emission levels across various trafﬁc scenarios. It
complements the Random Forest model by providing
alternative insights into hotspot detection and prediction.

## PDF page 17

NOx: A Harmful Pollutant
Why is NOx Targeting NOx in NOx Emissions
Considered the Most Threshold
Harmful Pollutant? Our Experiment NOx Emissions Threshold:
Health Impact: NOx is linked to Regulatory Focus: Due to Based on U.S. Environmental
serious respiratory issues and its severe health and Protection Agency (EPA)
contributes to the formation of environmental effects, NOx standards and NYC regulations.
ground-level ozone, which can is often prioritized in air We set the threshold for
aggravate asthma and other lung quality management nitrogen oxides (NOx)
diseases. strategies. emissions at 1.88 grams per
Environmental Concerns: NOx Our Models will treat the mile (g/mile).
emissions contribute to the NOx pollutant as the Rerouting Mechanism:
formation of ﬁne particulate target value for reduction. When a vehicle's predicted
matter (PM), leading to NOx levels exceed the 1.88
environmental degradation and g/mile threshold, we initiate the
affecting ecosystems. re-routing process.

## PDF page 18

Vehicle Re-routing Algorithm
● Our real-time vehicle re-routing algorithm
dynamically redirects high-pollution vehicles to
alternative routes (next shortest path to
destination)
● Console output displays rerouted vehicles and
their new paths, ensuring effective adjustments
during simulation.
● This approach enables continuous pollution
mitigation by adapting routes based on
real-time trafﬁc and pollution data.

## PDF page 19

03
Analysis &
Discussion

## PDF page 20

Initial
Emission
Levels in
Flushing
This map shows initial emission
levels in Flushing, with red zones
indicating trafﬁc congestion
hotspots where pollution is
highest.

## PDF page 21

Model Results:
Random Forest
NOx Levels After Random Forest Regressor
Model was applied to the simulation

## PDF page 22

Model Results:
XGBoosting
NOx Levels After XGB Model

## PDF page 23

RFR vs. XBG
CO2 CO NOx HC PMx
Random
Forest 72% 63.99 71.53% 65.31% 70.39%
Regressor
XGBoost 73.65% 70.15% 73.41% 70.72% 72.84%

## PDF page 24

NOx Levels:
Before vs. After

## PDF page 25

98,300,000
Big numbers catch your audience’s attention

## PDF page 26

Limitations of Scope: Focusing Solely on Cars
Narrow Focus Omitted Variables
This study exclusively examines Factors inﬂuencing emissions, such
emissions from cars, neglecting as road conditions, weather, and
other signiﬁcant contributors like trafﬁc behaviors, were not modeled,
trucks, buses, and motorcycles, each limiting the analysis.
with unique proﬁles
Data Constraints Implications
Limitations in data collection and The focus on a single vehicle type
simulation capabilities restricted the may result in an incomplete
inclusion of external inﬂuences like understanding of urban pollution
construction and pedestrian zones. dynamics.

## PDF page 27

Future Work: Expanding the Scope
Addressing Limitations
● Our research will broaden the model's scope to include a wider range of variables and real-world
conditions affecting emissions.
Integrate Environmental Factors
● Future models will consider weather, road conditions, and driving behaviors to enhance
understanding of trafﬁc emissions and their effects on air quality.
Real-World Applications
● Our goal is to reﬁne the model for practical use in densely populated areas like Flushing, NYC, to
improve public health and environmental quality.
Data-Driven Solutions
● By integrating machine learning models like XGBoost with real-time data, we aspire to help cities
manage trafﬁc and emissions more effectively, contributing to sustainable urban living.

## PDF page 28

As For Now
Reinforcement of Model Successful Emission
ML Potential Performance Reduction
This research highlights the The Random Forest We were able to reduce
transformative potential of Regressor Model emission levels by roughly 75%
machine learning in promoting performed exceptionally in the location of this case
urban environmental well during initial training study.
sustainability. and testing, achieving the
lowest MSE among all
Data Science Impact models. However, in Key Takeaways
real-time applications,
This work reﬂects the crucial role the XGBoost model Summarizing the project outcomes,
of data science in addressing outperformed it by we underscore the signiﬁcance of
environmental challenges, reducing air pollution at data-driven strategies in enhancing
emphasizing the need for higher rates. urban air quality.
innovative, effective solutions.

## PDF page 29

OUR TEAM
Mohammed Y Professor. X Huang Billy M Kyaw
Hossain
Project Leader Project Supervisor Data Scientist, Co-Partner
LinkedIn LinkedIn

## PDF page 30

“POLLUTION SHOULD NEVER BE THE
PRICE OF PROSPERITY”
— AL GORE

## PDF page 31

The End…
Do you have any questions?
CREDITS: This presentation template was created by Slidesgo, and includes
icons by Flaticon, and infographics & images by Freepik
By: Mohammed Y Hossain & Billy M Kyaw
