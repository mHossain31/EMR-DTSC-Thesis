# Text of ML_SUMO_ProjectReport.pdf (48 PDF pages, pypdf layout extraction)

## PDF page 1

Air Pollution Prediction and Reduction Strategies
in Urban Areas using SUMO and Machine
Learning
CollegeofEngineeringandComputing Sciences,NYIT
ProjectSupervisor:Prof.XHuang
DTSC 870ProjectI
By:
Mohammed Y Hossain(Leader) BillyM Kyaw
ID: [redacted] ID: [redacted]

## PDF page 2

Abstract
Urban air pollution remains one of the most pressing environmental challenges of our
time, impacting millions of people across the globe. It is a leading cause of serious health
conditions, including respiratory diseases, cardiovascular complications, and premature deaths.
Traffic emissions, in particular, contribute significantly to urban air quality degradation by
releasing harmful pollutants such as carbon dioxide (CO2), carbon monoxide (CO), nitrogen
oxides (NOx), hydrocarbons (HC), and particulate matter (PMx). With the continuous growth in
urban populations and vehicle densities, cities are increasingly grappling with the complexities
of managing and reducing air pollution. This has made the issue a top priority for urban planners,
environmental agencies, and policymakers.
In response to this challenge, simulation tools like SUMO (Simulation of Urban
Mobility) and advanced machine learning (ML) techniques offer innovative methodologies for
predicting, analyzing, and mitigating air pollution. SUMO allows for the simulation of realistic
traffic scenarios, enabling the collection of detailed emissions data across various urban settings.
By leveraging this data, ML models can be trained to predict pollution patterns, identify
hotspots, and inform targeted interventions. These interventions may include strategies such as
optimizing traffic flows, rerouting vehicles to avoid high-emission zones, and implementing
dynamic traffic control systems.
This study explores the integration of SUMO with machine learning to provide a
comprehensive approach to urban air pollution management. Through a detailed simulation of
traffic dynamics and emissions, the research aims to develop predictive models capable of
identifying air pollution hotspots in real time. Additionally, it proposes practical strategies to
reduce emissions, thereby contributing to healthier urban environments. The insights gained
from this work offer valuable guidance for city planners and environmental authorities in their
efforts to create sustainable, pollution-resilient cities, and promote public health and
environmental sustainability.
1

## PDF page 3

Table of Contents
Abstract.........................................................................................................................................................................................................................1
1. Introduction.............................................................................................................................................................................................................. 3
1.1 Environmental Objective................................................................................................................................................................................ 3
1.2 Research Scope............................................................................................................................................................................................... 4
2. Literature Review.....................................................................................................................................................................................................5
2.1 Related Works................................................................................................................................................................................................. 5
2.2 Research Objectives and Methodologies........................................................................................................................................................ 6
3. Data Collection & Simulation Setup...................................................................................................................................................................... 7
3.1 Urban map and traffic patterns (using OSMWebWizard)...............................................................................................................................8
- Figure 1: Flushing Map Network SUMO................................................................................................................................9
- Figure 2: Vehicle Movement in the Network................................................................................................................................. 10
3.2 Emission Pollutants Overview...................................................................................................................................................................... 10
3.3 SUMO Simulation Setup...............................................................................................................................................................................11
3.4 Emission Data Architecture.......................................................................................................................................................................... 12
- - Figure 3: Emissions Data Frame.................................................................................................................................................. 13
3.5 Vehicle & Traffic Dynamics..........................................................................................................................................................................13
- - Figure 4: Nox Emissions Flushing...................................................................................................................................... 15
4. Machine Learning Model Development...............................................................................................................................................................16
4.1 Overview of Machine Learning Models....................................................................................................................................................... 17
- - Figure 5: Machine Learning Models................................................................................................................................... 18
4.2 Pre-Model Air Pollution Levels....................................................................................................................................................................18
- - Figure 6: Initial Simulated Air Pollution.............................................................................................................................19
4.3 Development of Random Forest Regressor.................................................................................................................................................. 20
- - Figure 7: RF Model Train Set............................................................................................................................................21
- - Figure 8: RF Model Test Set............................................................................................................................................. 22
4.4 Development of XGBoost.............................................................................................................................................................................22
- - Figure 9: RF vs. XGB Test Set..........................................................................................................................................25
5. Real-Time Emission Reduction Application........................................................................................................................................................25
5.1 Real-Time Model Application...................................................................................................................................................................... 26
- - Figure 10: Real-Time Simulation Console Log................................................................................................................. 27
5.2 Marginal Errorin Real-Time Simulation...................................................................................................................................................... 28
6. Performance Analysis & Findings........................................................................................................................................................................29
6.1 Model Results: Random Forest Regressor....................................................................................................................................................30
- - Figure 11: NOx Levels After Random Forest Model.........................................................................................................31
6.2 Model Results: XGBoost.............................................................................................................................................................................. 32
- - Figure 12: NOx Levels After XGB Model.........................................................................................................................33
6.3 Random Forest Regressor vs. XGBoost....................................................................................................................................................... 33
- - Figure 13: Result Table Summary......................................................................................................................................34
- ............................................................................................................................................................................................... 36
- - Figure 14:Post Simulation Emissions Log......................................................................................................................... 36
6.4 Further Analysis............................................................................................................................................................................................37
- - Figure 15: Emission Data Scatter Plot............................................................................................................................... 39
- - Figure 16: Comparison of NOx Emissions........................................................................................................................ 40
7. Discussion................................................................................................................................................................................................................41
7.1 Limitations of Scope: Focusing Solely on Cars............................................................................................................................................41
7.2 Future Work and Broader Impact..................................................................................................................................................................43
- - Figure 17: The Grater Map of Flushing , NY.....................................................................................................................43
8. Conclusion...............................................................................................................................................................................................................44
8.1 Special Thanks.............................................................................................................................................................................................. 46
9. References............................................................................................................................................................................................................... 46
2

## PDF page 4

1. Introduction
1.1 Environmental Objective
Urban air pollution is a critical environmental and public health challenge with
wide-ranging effects that permeate multiple sectors, impacting millions of individuals
worldwide. The major pollutants contributing to this issue—carbon dioxide (CO2), carbon
monoxide (CO), nitrogen oxides (NOx), hydrocarbons (HC), and particulate matter
(PMx)—are largely attributed to vehicular emissions, industrial operations, and energy
production. Among these, vehicular emissions are particularly problematic, especially in
densely populated urban areas where traffic congestion is frequent and persistent.
The rapid expansion of urban populations and the corresponding increase in vehicle
usage have intensified traffic emissions, significantly intensifying urban air quality issues.
This is a major concern, as prolonged exposure to elevated levels of pollutants has been
consistently linked to severe health risks, including respiratory ailments such as asthma and
bronchitis, cardiovascular diseases, and an increased risk of premature death. Beyond human
health, the environmental impacts of air pollution are equally profound, contributing to
phenomena like acid rain, diminished visibility, and the acceleration of climate change due to
the accumulation of greenhouse gasses.
As urban centers continue to grow and traffic density rises, managing and mitigating
traffic-induced air pollution presents an increasingly complex challenge for city planners and
environmental regulators. Traditional approaches to monitoring, controlling, and mitigating
air pollution, such as static air quality stations or predefined emission standards, have proven
inadequate in dealing with the dynamic and evolving nature of urban environments. These
methods often lack the real-time flexibility and adaptability needed to address rapid changes
in traffic patterns and pollution levels, especially in high-density areas.
Given these limitations, there is an urgent need for innovative approaches capable of
accurately predicting pollution levels and developing effective emission reduction strategies
3

## PDF page 5

tailored to the complexities of urban traffic systems. This project seeks to address the issue of
urban air pollution, with a focus on traffic-related emissions, by leveraging the Simulation of
Urban Mobility (SUMO) platform—a high-resolution, microscopic traffic simulation tool.
SUMO will be used to model realistic urban traffic scenarios and generate emissions data,
which will serve as the foundation for building predictive models.
1.2 Research Scope
The primary goal of this project isto develop machine learning (ML) models using emissions
data generated through SUMO (Simulation of Urban Mobility) to predict pollution levels in
diverse urban environments. By simulating real-time traffic dynamics and vehicle emissions,
the project aims to identify pollution hotspots and assess potential strategies for reducing
emissions. These strategies include traffic flow optimization and dynamic vehicle rerouting,
both of which are tested and evaluated within the SUMO simulation framework to measure
their effectiveness in minimizing traffic-induced air pollution.
By combining advanced machine learning techniques with detailed traffic simulations, this
research offers valuable insights and data-driven strategies for urban planners and
environmental authorities. The ultimate goal is to inform the development of more
sustainable traffic management systems that can reduce the impact of vehicular emissions on
urban air quality, ultimately promoting healthier urban living environments and improving
public health outcomes.
However, the scope of this research is not without limitations. Due to constraints in
computational power and the availability of tools, the project remains confined to the realm
of simulation rather than real-world implementation. The reliance on SUMO for traffic and
emissions data, while powerful, limits the project to modeled scenarios rather than direct
application to real-world traffic conditions and pollution data. As such, the findings are
valuable within the context of simulation but have yet to be validated in real-world urban
environments.
4

## PDF page 6

Despite these limitations, the research has made the most of the resources available, allowing
us to focus on specific aspects of traffic and emissions patterns, offering a detailed
exploration of how machine learning can contribute to pollution prediction and reduction
strategies. While this project does not extend to real-world deployment, it lays the
groundwork for future expansion. We are optimistic that with advances in tools,
computational capacity, and real-time data collection, our findings can be tested and refined
in practical applications.
Looking ahead, we hope to translate this research into real-world action, where the strategies
developed here could play a crucial role in reducing emissions and improving urban air
quality. The future offers the opportunity to bridge the gap between simulation and reality,
putting our findings into practice to make a tangible impact on reducing urban air pollution
and preserving the environment.
2. Literature Review
This section critically examines prior research on air pollution prediction and mitigation
strategies, with a focus on the integration of machine learning (ML) models and traffic
simulation tools such as SUMO. The studies reviewed are organized into two subsections:
Related Works and Research Objectives and Methodologies. By analyzing these works, this
review establishes a comprehensive understanding of the current advancements in the field and
how they contribute to and inform the objectives of our study.
2.1 Related Works
Several research efforts have employed machine learning models and traffic
simulation to predict and manage air pollution in urban environments. A study by Jiang et
al. (2022) aimed to identify patterns in the use of ML for air pollution prediction,
specifically focusing on pollutants like CO2, NOx, and particulate matter (PM). By
5

## PDF page 7

reviewing over 900 papers, the study found that regression models and deep learning
techniques, such as neural networks, were frequently applied due to their ability to capture
complex, non-linear relationships between traffic emissions and air quality (MDPI).
Similarly, Lin et al. (2020) used the SUMO simulation tool to model urban traffic
and generate emissions data from real-world taxi trajectories. This data was then fed into
machine learning algorithms to predict pollutant concentrations in different areas of the
city. Their methodology combined real-time traffic simulations with ML techniques,
showcasing the potential of SUMO for generating reliable emissions data and using that
information to model pollution dynamics (SpringerLink).
Another key study by Dong et al. (2021) employed reinforcement learning to
dynamically reroute vehicles away from pollution hotspots detected in real-time. The study
leveraged real-time traffic and emissions data to adjust vehicle routes and mitigate traffic
congestion, which is a significant contributor to elevated pollutant levels (SpringerLink).
Javid et al. (2022) further expanded on this by exploring the optimization of traffic signal
timings, combined with vehicle rerouting strategies, to reduce the emission of CO2 and
NOx in congested urban areas (SpringerLink).
2.2 Research Objectives and Methodologies
The results from these studies consistently highlight the significant role of
machine learning in predicting and reducing traffic-induced pollution. Jiang et al.(2022)
demonstrated that ML algorithms, particularly deep learning models, offer high accuracy
in predicting urban air quality across different pollutant types. Lin et al. (2020) found that
the integration of SUMO with real-world traffic data significantly improved the spatial
and temporal accuracy of pollution predictions, helping to localize pollution hotspots
more effectively than traditional models.
In terms of emission reduction strategies, the findings from Dong et al. (2021)
showed that dynamic vehicle rerouting could reduce overall pollution levels by up to
6

## PDF page 8

15%, with the most notable decreases in congested areas. This approach also
demonstrated the potential to minimize traffic-related pollution spikes during peak hours.
Javid et al. (2022) further noted that by optimizing traffic signals in tandem with
rerouting strategies, it was possible to reduce NOx and CO2 levels by as much as 20% in
highly populated areas.
These prior studies provide a strong foundation for our project, which also seeks
to use machine learning and traffic simulation tools to predict and reduce traffic-related
air pollution. While these studies show promising results in the realm of simulation and
theoretical application, they have often been limited to simulated environments rather
than real-world implementation, a limitation that our research shares. However, our
project expands upon these methods by not only focusing on pollution prediction but also
exploring emission reduction strategies such as traffic flow optimization and rerouting,
which are tested within SUMO simulations. Although our current work is confined to
simulation, future research could apply these models to real-world urban environments,
offering a pathway for urban planners and policymakers to reduce emissions and improve
air quality.
3. Data Collection & Simulation Setup
This study focuses on Downtown Flushing, a highly congested neighborhood in Queens,
New York City. Known as NYC's largest Chinatown, Downtown Flushing ischaracterized by its
dense population and constant traffic flow, making itan ideal location for air pollution studies.
The area experiences heavy vehicular activity around the clock, primarily due to itscommercial
and residential significance. By selecting this site, we aim to model and predict pollution levels
that reflect real-world conditions of urban congestion. Data for this research was derived from
SUMO simulations, where traffic flow patterns, vehicular movements, and emission data were
modeled based on real-world conditions in Flushing. This dense urban landscape allows us to
7

## PDF page 9

analyze the relationship between traffic dynamics and air pollution, providing a reliable basis for
testing machine learning models for emission prediction and mitigation strategies.
3.1 Urban map and traffic patterns (using OSMWebWizard)
To model the traffic patterns in Downtown Flushing, we utilized the
OSMWebWizard tool, which allowed us to generate a detailed urban map of the area. The
OpenStreetMap (OSM) data provided the foundation for accurately simulating the road
network, intersections, and traffic flows in this highly congested neighborhood. However,
due to the specificity of our study, publicly available datasets related to real-world traffic
patterns and pollution levels in this area were limited. This lack of accessible data posed a
challenge, as existing traffic datasets did not adequately reflect the unique characteristics of
Flushing’s continuous traffic congestion.
As a result, we relied heavily on generating synthetic traffic data using the SUMO
simulation tool. By extensively running simulations based on the actual road network from
OSM, we created realistic traffic scenarios that mirrored the 24/7 heavy traffic flow in
Flushing. These simulations accounted for vehicle density, road structure, and typical traffic
conditions, ensuring the data reflected the high traffic volume experienced in the area.
Although this data was generated rather than collected from real-world sources, it was
critical for conducting our experiments in predicting pollution levels and testing emission
reduction strategies.
In Figures 1 and 2, we observe critical aspects of the urban traffic patterns modeled
in our SUMO simulation. Figure 1 showcases a comprehensive view of the Downtown
Flushing area, displaying the entire street network in a detailed layout. The green lines
indicate the road infrastructure, including the main streets, intersections, and residential
areas. The intricate layout effectively represents the real-world configuration of Flushing’s
streets, allowing for an accurate simulation of traffic flow under various conditions. Every
road segment and intersection plays a role in mimicking the urban grid’s complexity, and the
map accurately incorporates the densely populated structures and thoroughfares. Figure 2
provides a closer look at a single intersection within the area, where we can see the
8

## PDF page 10

individual vehicles modeled in the simulation. Here, vehicles are depicted waiting at a red
light, offering a fine-grained perspective on how traffic is controlled by signals. This
zoomed-in snapshot captures the micro-dynamics of traffic behavior, including how vehicles
respond to traffic lights and congestion at intersections. The vehicles are positioned
realistically as they would be at a busy intersection, and the model takes into account signal
timing, stop-and-go traffic patterns, and vehicle spacing.
- Figure 1:Flushing Map Network SUMO
9

## PDF page 11

- Figure 2: VehicleMovement inthe Network
These visual representations help emphasize the intricate level of detail that went
into simulating real-world traffic conditions for our study area. Despite the limitations in
accessing external data, the simulations generated in SUMO offer a solid foundation for our
subsequent analyses on pollution and traffic optimization strategies.
3.2 Emission Pollutants Overview
The emissions data generated from the SUMO simulation focus on several key pollutants
that significantly impact air quality:
❖ CO2 (Carbon Dioxide): This greenhouse gas is the primary contributor to
global warming and climate change. Its levels increase with vehicle emissions,
making ita critical factor in air quality assessments.
❖ CO (Carbon Monoxide): Carbon monoxide isa colorless, odorless, and
highly toxic gas. Prolonged exposure to CO can lead to serious health issues,
10

## PDF page 12

including impaired heart and lung function, particularly in areas with heavy traffic
congestion.
❖ NOx (Nitrogen Oxides): Nitrogen oxides are significant pollutants linked to
respiratory conditions like asthma. NOx also plays a key role in the formation of
smog and ground-level ozone, further degrading urban air quality and contributing to
health risks.
❖ HC (Hydrocarbons): Hydrocarbons contribute to the formation of ozone
and smog. Many of these organic compounds are toxic and can cause respiratory
issues, exacerbating the health impacts in urban environments.
❖ PMx (Particulate Matter): Particulate matter, especially fine particles
(PM2.5 and PM10), poses significant health risks. These particles can penetrate deep
into the lungs and bloodstream, increasing the likelihood of respiratory and
cardiovascular diseases.
The simulation systematically collects emissions data for each vehicle operating within the
network. Factors such as vehicle type, engine efficiency, speed, and road conditions
influence the emission rates. Analyzing this data helps to identify high-pollution zones and
the specific pollutants contributing most to air quality deterioration. This information is
crucial for developing traffic rerouting strategies aimed at mitigating pollution and
protecting public health.
3.3 SUMO Simulation Setup
To accurately capture emission data during the simulation, the SUMO configuration
file (.sumocfg) required modifications to ensure that the appropriate data collection
modules were enabled. Specifically, directives were added to instruct SUMO to generate an
emissions.xml file during the simulation run. This filecontains detailed information about
pollutants emitted by each vehicle, including CO2, CO, NOx, HC, and PMx levels. By
doing so, we ensured that the simulation environment could provide the raw air pollution
data necessary for subsequent machine learning model development.
11

## PDF page 13

The simulation was conducted using the Flushing urban map, where vehicles were
dynamically routed through the network. During the simulation, real-time emissions data
were continuously logged in the emissions.xml file. This data serves as the foundation for
the next phase of the project, which involves analyzing pollutant levels and using machine
learning models to predict and reduce air pollution in criticalareas.
For this experiment, Python was used in conjunction with Jupyter Notebook to
interact with the SUMO simulation via the TraCI (Traffic Control Interface) API. TraCI
allowed for the management of various aspects of the simulation, such as vehicle
movements, data extraction, and dynamic traffic rerouting. This setup provided a flexible
and efficient workflow, ensuring that the simulation environment could be both controlled
and monitored for real-time data collection essential to the project's goals.This setup
provided a highly flexible and scalable framework for conducting large-scale urban
simulations, while ensuring that key data emissions and traffic dynamics were captured
with the necessary precision.
3.4 Emission Data Architecture
The transformation of raw emissions data collected from the SUMO simulation into
a structured format for analysis is a pivotal step in this project. This process involves
parsing the emissions data stored in an XML file, which serves as the output of the
simulation. By extracting relevant information, we can utilize advanced data manipulation
and analytical tools offered by libraries such as Pandas. During this extraction process, the
XML structure is traversed to identify and retrieve key attributes for each vehicle,
including carbon dioxide (CO2), carbon monoxide (CO), nitrogen oxides (NOx),
hydrocarbons (HC), particulate matter (PMx), and the vehicle's spatial coordinates (X and
Y). This structured approach not only facilitates the organization of the data but also
ensures that we retain essential details for further analysis. Each record includes a
timestamp, vehicle identifier, and pollution metrics, enabling us to correlate emissions with
specific vehicles and timeframes. The resulting dataset is organized into a Pandas
12

## PDF page 14

DataFrame, which provides a user-friendly format for subsequent data analysis. This
DataFrame, illustrated in Figure 3, showcases the first five rows of the emissions data.
Each column represents a distinct variable:
❖ Time indicates the simulation timestep,
❖ Vehicle_ID uniquely identifies each vehicle,
❖ CO2, CO, NOx, HC, and PMx represent the respective emissions measured
for each vehicle, X and Y provide the spatial coordinates of the vehicles ateach timestep.
-
- - Figure 3: Emissions Data Frame
Figure 3 effectively demonstrates the volume and structure of the emissions data
collected, with the DataFrame comprising 638,367 rows. This extensive dataset will be
critical for the next phase of the project, where advanced modeling techniques will be
employed to analyze the impact of vehicle emissions on air quality. The comprehensive
nature of this data enables us to identify pollution hotspots and assess the effectiveness of
potential mitigation strategies.
3.5 Vehicle & Traffic Dynamics
In this section, we focus on the dynamic vehicle rerouting strategy implemented in
our simulation, which aims to optimize trafficflow and reduce emissions in high-pollution
areas. By employing a real-time pollution detection model, we can reroute vehicles away
13

## PDF page 15

from predicted or detected pollution hotspots, reducing overall emissions and improving
traffic congestion. This strategy ensures that vehicles traveling through the simulated urban
environment follow alternative paths when the air quality in certain areas deteriorates,
promoting cleaner and more efficient movement throughout the neighborhood.
The rerouting strategy works by continuously monitoring the emissions generated
by each vehicle at every step of the simulation. As vehicles travel through the map, their
emissions data—including CO2, CO, HC, and PMx—is collected. These pollutant levels
are used as input features to the predictive model, which estimates the NOx levels for each
vehicle. If the predicted NOx exceeds a pre-defined pollution threshold, the system flags
the vehicle as contributing to poor air quality and triggers the rerouting mechanism.
Once a high-pollution event is detected, the rerouting function seeks to redirect the
affected vehicle away from its current path. The system identifies the vehicle’s current
position and its intended destination, then searches for an alternative, less-polluted route
using SUMO's built-in routing capabilities. Ifa viable alternative route is found, the vehicle
is rerouted, potentially reducing emissions in the hotspot area and redistributing traffic to
avoid congestion. If no suitable route is available, the vehicle continues on its original path,
but the simulation ensures that the overall network stillbenefits from this adaptive traffic
control.
This high-level rerouting strategy balances the dual goals of reducing emissions and
maintaining smooth traffic flow. By preventing vehicles from contributing further to
pollution hotspots, the system not only improves air quality but also alleviates traffic
congestion in those areas. The logged data on rerouted vehicles and pollution hotspots
provides valuable insights for further refining traffic management strategies and improving
urban mobility in environmentally conscious ways.
14

## PDF page 16

-
- Figure 4: Nox Emissions Flushing
-
Figure 4 illustrates the pollution levels across the Flushing neighborhood before the
rerouting strategy is applied. This SUMO map network shows the spatial distribution of
NOx emissions (measured in arbitrary units) as predicted by the initial simulation. Darker
areas in the figure correspond to higher NOx concentrations, indicating the locations where
traffic-induced pollution is most concentrated. The visualization highlights significant
pollution hotspots, primarily along main traffic arteries, which are targeted for rerouting
once the model isfully deployed. These insights serve as the foundation for developing a
more sustainable and efficient traffic management strategy, reducing pollution and
improving the quality of life in urban environments.
In our rerouting strategy, we set the threshold for nitrogen oxides (NOx) emissions
at1.88 grams per mile. This value is based on regulatory standards set by New York City to
manage air quality, particularly in congested urban areas. NOx is measured in grams per
mile (g/mile) emitted by each vehicle. These emissions contribute to harmful pollutants
15

## PDF page 17

such as ground-level ozone and fine particulate matter, which can exacerbate respiratory
issues and environmental degradation. According to the U.S. Environmental Protection
Agency (EPA) standards and local NYC regulations, managing NOx emissions is crucial in
reducing smog and improving urban airquality.
The NOx threshold of 1.88 g/mile is chosen because italigns with NYC's air quality
management goals, which aim to maintain pollutant levels within safe limits to protect
public health. When the model predicts that NOx levels for any given vehicle exceed this
threshold, we trigger the vehicle rerouting process. By keeping NOx levels below this
threshold, we can ensure that traffic emissions are kept within regulated limits, helping to
reduce the concentration of pollution hotspots.
4. Machine Learning Model Development
In this chapter, we will focus on the development of machine learning models to predict
airpollution hotspots in the Flushing neighborhood based on the traffic emissions data collected
from our simulations. Various machine learning algorithms will be tested to evaluate their
suitability for predicting nitrogen oxide (NOx) emissions and identifying pollution hotspots on
the map. Given the complexity of traffic flow and air pollution dynamics, models such as
Random Forest Regressor, Gradient Boosting, and Neural Networks are particularly well-suited
to handling this scenario due to their ability to capture non-linear relationships and interactions
between features.
From this pool of models, we will select the two best-performing ones based on metrics
such as Mean Squared Error (MSE) and model explainability. These top-performing models will
then be further fine-tuned and compared in terms of their prediction accuracy and computational
efficiency. The ultimate goal is to determine which model is most effective for identifying
pollution hotspots in real-time, thus enabling better rerouting strategies to reduce both traffic
congestion and emissions.
16

## PDF page 18

4.1 Overview of Machine Learning Models
In the Machine Learning Model Development phase, we evaluated a range of models
to predict airpollution hotspots, focusing on their capacity to minimize error and accurately
model pollution levels in urban areas. Air pollution modeling, especially in densely
populated cities like New York, is inherently complex due to the numerous variables that
contribute to emissions, such as traffic flow, vehicle types, and environmental factors.
Machine learning models offer a powerful approach in capturing these nonlinear and
dynamic relationships between traffic patterns and emissions, helping to predict where
pollution islikely to accumulate in real time.
We tested several machine learning models, including Random Forest, XGBoost,
Gradient Boosting, Linear Regression, Ridge Regression, K-Nearest Neighbors, Elastic Net,
and Neural Networks. Each model was chosen based on its potential for handling the
complexity of the dataset. For example, ensemble methods like Random Forest and
XGBoost are known for their robustness and ability to handle high-dimensional data,
making them ideal candidates for this scenario. These models excel in capturing intricate
patterns, particularly when dealing with large datasets and many input variables such as
emission types, vehicle positions, and trafficintensity.
Figure 5 provides a comparative analysis of the models' performance in terms of
their testing MSE. The Random Forest model achieved the lowest MSE (0.000105),
followed closely by XGBoost (0.000533), indicating that these models were the most
effective in predicting pollution hotspots based on the dataset. Both models leverage
decision trees, which are particularly well-suited to tasks involving complex decision
boundaries. In contrast, other models like Gradient Boosting, Linear Regression, and Ridge
Regression had higher error rates, and the Neural Network model had the highest MSE
(0.016439), suggesting itwas less effective in capturing the relationships in the data.
17

## PDF page 19

- -Figure 5: Machine Learning Models
Given their superior performance in minimizing error, Random Forest and XGBoost
were selected for further development. These models' ability to generalize well on the test
data makes them suitable for the task of real-time simulation and prediction of pollution
hotspots. Their accuracy in predicting pollution levels will be critical for devising strategies
tomitigate emissions and improve air quality in urban environments.
4.2 Pre-Model Air Pollution Levels
Before applying our machine learning models, we first analyzed the air pollutant
levels captured during the initial simulation of traffic emissions in New York City. The
purpose of this analysis was to understand the baseline pollution levels, which we aim to
reduce by rerouting traffic based on real-time predictions. The dataset from the simulation
18

## PDF page 20

includes critical pollutants like NOx, CO2, CO, PMx, and HC, which were measured across
various vehicles and locations.
-
-
-
- -Figure 6: InitialSimulated Air Pollution
-
The plots generated from the emissions data indicate the spatial and temporal
distribution of pollution hotspots in the city. High levels of NOx and CO2 were recorded in
congested areas, reflecting the impact of traffic density on emission levels. Our goal is to
19

## PDF page 21

develop and apply machine learning models capable of detecting such hotspots inreal-time
and predicting potential high-pollution zones based on traffic patterns.
By integrating Random Forest and XGBoost models into the real-time simulation,
we intend to reroute traffic dynamically to reduce these pollutant levels. Through continuous
monitoring and prediction, the models will suggest optimal traffic flows, reducing
congestion in high-emission areas. The performance of the models will be evaluated by
comparing post-model pollutant levels to these initial levels, aiming for a significant
reduction in NOx and other harmful gasses. This approach aligns with the city’s
environmental goals to mitigate air pollution and improve urban air quality.
4.3 Development of Random Forest Regressor
In the development of the Random Forest Regressor model, the objective is to
predict nitrogen oxide (NOx) levels based on the emissions of other pollutants, such as CO2,
CO, HC, and PMx. The dataset is split into features (CO2, CO, HC, PMx) and the target
variable (NOx), which is the main pollutant we aim to control. After this, the data is split
into training and testing sets, typically using a test size of 20% to evaluate model
performance without overfitting.
The Random Forest Regressor is chosen due to its effectiveness in regression tasks
with high-dimensional data. It is an ensemble method that aggregates predictions from
multiple decision trees to reduce variance and avoid overfitting. In this implementation, the
model was trained using 100 trees (n_estimators=100), which strikes a balance between
performance and computational efficiency.
The figures provided illustrate the model’s performance on both the training and
testsets. In Figure 7, the model’s predictions on the training set are compared against actual
NOx levels. The overlap between predicted and actual NOx levels demonstrates the model's
20

## PDF page 22

strong fit to the training data, though some variance still exists, likely indicating room for
further tuning of model hyperparameters or additional feature engineering.
- - Figure 7: RF Model Train Set
Figure 8 shows the model's performance on the test set, which offers a better gauge
of its ability to generalize. Here, the predicted NOx levels also track closely to the actual
values, although some deviations suggest slight overfitting on the training set. However, the
overall performance is strong, with minimal differences between training and test
predictions, demonstrating that the Random Forest model is well-suited for the task of
predicting NOx levels in real time.
21

## PDF page 23

- - Figure 8: RF Model TestSet
-
Additionally, this model can be deployed within the SUMO simulation to
dynamically reroute vehicles in high-pollution scenarios. By using the predicted NOx levels,
the simulation identifies hotspots where emissions exceed a defined threshold, allowing the
model to suggest alternative routes to reduce overall pollution, contributing to real-time
pollution management.
4.4 Development of XGBoost
The XGBoost model in this project is designed for predicting NOx levels based on
emissions and positional data. XGBoost (Extreme Gradient Boosting) is a highly efficient
and flexible machine learning algorithm that uses an ensemble of decision trees to improve
predictive accuracy. The model operates by constructing multiple weak learners (decision
22

## PDF page 24

trees) in a sequential manner, with each tree trying to correct the errors of its predecessor.
This boosting technique helps in minimizing overfitting and allows the model to handle
complex, non-linear relationships between input variables.
The key parameters used in this XGBoost implementation include:
❖ Objective: The reg:squarederror objective function is selected, which is standard
for regression tasks. It minimizes the squared differences between predicted and
actual NOx values, thus ensuring the model accurately predicts continuous output
values.
❖ n_estimators: The number of trees (estimators) is set to 100, which controls how
many boosting rounds are conducted. A higher number of trees generally
increases model complexity and training time, but it also allows the model to
capture more intricate patterns in the data. In this case, 100 estimators strike a
balance between accuracy and computational efficiency.
❖ random_state: Setting random_state to 42 ensures reproducibility by controlling
the random number generation for splitting data into training and testing sets.This
allows for consistent results across multiple training sessions.
The training process begins with the model building the first decision tree to predict
NOx levels. Each subsequent tree focuses on correcting the residuals (errors) made by the
previous trees, enhancing the model's ability to generalize well on unseen data. As a result,
the XGBoost model not only captures the relationships between emissions variables and
NOx levels but also adapts dynamically to account for real-time variations in traffic and
environmental conditions.
XGBoost’s advantage lies in its robustness and ability to handle large datasets
efficiently. By tuning its parameters, such as the learning rate, max depth, and number of
estimators, further improvements in accuracy could be achieved. Moreover, the model’s
23

## PDF page 25

regularization techniques, such as L1 (Lasso) and L2 (Ridge) regularization, help in
controlling overfitting, making it ideal for dynamic and fluctuating urban environments
where air pollution levels can change rapidly.
Finally, the trained model is saved for further deployment in real-time simulations,
allowing for continuous prediction of NOx levels and supporting dynamic rerouting
strategies to mitigate pollution in hotspot areas.
The performance of the Random Forest and XGBoost models on the test set, as seen
in the visualized results, reveals important insights into their predictive capabilities. The top
plot represents the Random Forest model's predictions, which generally follow the trend of
the actual NOx levels but exhibit a degree of over-smoothing. The overall pattern shows that
the model can capture the broader dynamics of NOx fluctuations, but the finer variations
and spikes in the actual NOx values are somewhat muted. This behavior is consistent with
the ensemble averaging effect of Random Forest, which tends to produce smoother
predictions by aggregating the outputs of multiple decision trees.
In contrast, the XGBoost model's performance, illustrated in the bottom Figure 9,
demonstrates a closer alignment with the actual NOx levels. The model is able to capture the
high-frequency variations and spikes in NOx values more effectively than the Random
Forest model. This reflects XGBoost's ability to optimize performance through gradient
boosting, allowing it to focus on minimizing errors in regions where the Random Forest
model may have struggled. As a result, the XGBoost model displays greater sensitivity to
fluctuations in the data, making it potentially more suitable for real-time applications where
precision is crucial.
24

## PDF page 26

- - Figure 9:RF vs.XGB TestSet
-
With both models trained and evaluated, they are now prepared to be integrated into
the real-time simulation. Their respective strengths—Random Forest's stability and
XGBoost's precision—will be leveraged to detect and reduce NOx levels dynamically
during the simulation.
5. Real-Time Emission Reduction Application
In this section, we will implement the trained machine learning models—the Random
Forest Regressor and XGBoost models—into real-time traffic simulations to assess their ability
to reduce vehicular emissions dynamically. The goal of this experiment is to analyze the
25

## PDF page 27

effectiveness of these models in real-time applications by utilizing them to reroute traffic in
response to detected NOx levels and subsequently collect the emissions data post-application.
The real-time simulation will be conducted twice: once with the Random Forest
Regressor model and once with the XGBoost model. During each simulation, dynamic rerouting
will be triggered by pollution levels predicted by the respective model. This rerouting aims to
alleviate air pollution hotspots by redistributing traffic flow in a way that minimizes NOx
emissions. After each simulation, a new dataset will be generated, which will capture car
emissions data following the application of the rerouting strategies.
The first simulation will involve applying the Random Forest Regressor model, after
which the collected dataset will reflect emission levels post-optimization. Similarly, in the
second simulation, we will apply the XGBoost model, and the resulting dataset will provide a
comparison of NOx levels after the intervention. These new datasets will be used in the next
section to perform an in-depth analysis of the models' efficacy in reducing vehicular emissions,
and to identify which model achieves greater emission reductions in real-time.
5.1 Real-Time Model Application
During the real-time simulation, both the Random Forest Regressor and XGBoost
models continuously monitor vehicular emissions to predict high pollution zones or
"hotspots" based on NOx levels. As the simulation progresses, the models prove their
efficacy by actively detecting these hotspots and dynamically rerouting vehicles to mitigate
further emissions in affected areas. The following console output illustrates this process,
where vehicles are detected to be contributing to elevated pollution levels, triggering the
rerouting mechanism.
High pollution detected for veh0 on edge 275281192#1.
Rerouting...
26

## PDF page 28

Vehicle veh0 rerouted to reduce pollution. New route:
('275281192#1', '49175637#5', '49175637#7', '49175637#9',
'49175637#12', '49175637#14', '49175637#15', '663513503#2',
'25745903#0', '25745903#2', '25745903#5', '25745903#7',
'25745903#9', '25745903#11')
High pollution detected for veh3 on edge :42873533_3.
Rerouting...
Vehicle veh3 rerouted to reduce pollution. New route:
(':42873533_3', '5705230#2', '5706595#1', '663513505#1',
'663513505#4', '663513505#7', '822071223#0', '-220470240#4',
'219624524#0', '219624524#4', '-219969534#3', '5704723#0',
'5704723#2', '5704723#5', '-5702732#13', '-5702732#9',
'-5702732#6', '-49175636#1')
High pollution detected for veh1 on edge -5707650#7.
Rerouting...
Vehicle veh1 rerouted to reduce pollution. New route:
('-5707650#7', '5707235#12', '5707744#0', '5707744#2',
'5707744#4', '25745903#11', '-5710187#1')
- -Figure 10: Real-Time SimulationConsole Log
For instance, the message, "High pollution detected for veh0 on edge 275281192#1.
Rerouting..." indicates that the model has identified high NOx emissions from vehicle veh0
on a specific road segment (edge 275281192#1). In response, the vehicle is immediately
rerouted, with the new route displayed as a sequence of road segments that divert itaway
from the polluted area. The rerouting decision is made dynamically, adapting to real-time
trafficand environmental conditions to minimize overall emissions.
Similarly, the recurring messages for other vehicles like veh1 and veh3—"High
pollution detected for veh3 on edge :42873533_3"—demonstrate the model’s active role in
real-time pollution management. Each rerouted vehicle isassigned an alternative path, such
as the new route for veh3, which includes segments like '5705230#2', '5706595#1',
'663513505#1', and so on. This real-time adjustment prevents vehicles from further
contributing to pollution hotspots, thereby promoting better air quality across the simulation
environment.
The consistent rerouting messages, which occur in near real-time, indicate the
models are successfully detecting areas with high NOx emissions and making predictive
decisions to redirect vehicles. This functionality showcases the models' dynamic
27

## PDF page 29

capabilities, proving that the integration of machine learning with traffic management can
effectively reduce vehicular pollution. These rerouting interventions will later be evaluated
by comparing the emission data collected from the post-simulation datasets.
5.2 Marginal Error in Real-Time Simulation
When conducting real-time simulations, the accuracy of the results is influenced by
various factors that can introduce a margin of error. These errors arise from discrepancies
between the predicted behavior of the model and the actual outcomes observed during the
simulation. In the case of our simulation for reducing vehicle emissions through dynamic
rerouting, several sources of error can affect the results:
❖ Prediction Uncertainty: Both the Random Forest and XGBoost models, while
highly accurate, have inherent prediction uncertainty. This may result in
occasional misclassifications of pollution hotspots or suboptimal rerouting
decisions.
❖ Traffic Flow Variability: The real-time simulation environment includes
complex and unpredictable traffic dynamics. Factors such as random vehicle
arrivals, changes in speed, and interactions between vehicles on congested edges
can lead to variations in emissions that are difficult to fully account for.
❖ Environmental Variability: Weather, time of day, and other external factors not
accounted for in the model can affect vehicle emissions, leading to a slight
deviation in the expected results.
Efforts to Minimize the Margin of Error:
To mitigate these sources of error and ensure the results are as reliable as possible,
we have taken the following steps in the simulation:
28

## PDF page 30

❖ Consistent Simulation Settings: All simulation parameters, such as vehicle counts,
traffic light timings, and edge definitions, have been kept consistent across
different runs of the simulation. This consistency is crucial to ensure that any
changes in emissions are solely due to the models' interventions rather than
differences in the underlying simulation environment.
❖ Fixed Location for Analysis: We have applied both the Random Forest and
XGBoost models to the same geographic area—Flushing, New York. By focusing
on a single location with itsunique traffic patterns, road networks, and historical
pollution data, we reduce variability due to location-specific factors. This
approach allows for a fair comparison between the models while minimizing
extraneous noise in the data.
❖ Multiple Simulation Runs: Running the simulation multiple times and averaging
the results further helps to minimize random fluctuations in emissions. Each run
captures slightly different traffic behaviors, and averaging across runs reduces the
impact of outlier events.
By maintaining control over these factors, we ensure that the models are applied
under the same conditions and that the real-time emission reduction results reflect the
performance of the models rather than random variability in the simulation environment.
This strategy ultimately reduces the margin of error and provides a more robust foundation
for the emission reduction analysis in the next section.
6. Performance Analysis & Findings
This chapter presents a comprehensive performance analysis of the machine learning
models—Random Forest and XGBoost—in predicting nitrogen oxide (NOx) emissions during
real-time simulations. We will evaluate the effectiveness of these models in identifying pollution
29

## PDF page 31

hotspots and executing dynamic vehicle rerouting to mitigate emissions. By systematically
comparing the actual NOx levels with the model-generated predictions, we aim to assess the
accuracy and reliability of each approach. This analysis will illuminate both the strengths and
limitations inherent in each model, providing valuable insights into their practical applicability in
urban traffic management. Ultimately, the findings will inform strategies for further refinement
of emission reduction techniques in densely populated environments.
6.1 Model Results: Random Forest Regressor
The results of the Random Forest Regressor model's application to the SUMO
simulation of the Flushing map are illustrated in Figure 11. This figure represents the
predicted NOx emission levels after the rerouting of vehicles, as modeled by the Random
Forest algorithm. Compared to the initial pollution map (also shown above), where high
levels of NOx concentrations were widespread throughout the map, the post-application
map reveals a significant reduction in emissions.
In the original map, large portions of the streets were marked in deep red, indicating
zones with NOx levels as high as 12 units (µg/m³), particularly in high-traffic areas and road
intersections. This reflects the baseline pollution levels before any traffic rerouting strategies
were applied.
However, after applying the Random Forest Regressor model, the updated emission
map shows a visible decrease in NOx concentrations across these critical areas. The spots
previously showing the highest levels of pollution are now minimized, with fewer instances
of deep red. Most regions have shifted towards lighter blue shades, indicating lower NOx
levels, particularly around key traffic arteries where pollution was initially concentrated.
This comparison demonstrates the model's effectiveness in predicting pollution
hotspots and rerouting vehicles accordingly, which led to a substantial improvement in air
quality throughout the map. By dynamically adjusting the vehicle routes in real time, the
30

## PDF page 32

Random Forest Regressor succeeded in mitigating the pollution burden, as reflected in the
substantial changes in the NOx distribution pattern.
- -Figure 11: NOx Levels AfterRandom Forest Model
This comparison of the two maps showcases how the implementation of machine
learning models in urban traffic management can actively reduce air pollution, making this
approach an efficient tool for improving environmental conditions in congested areas like
Flushing, NY.
31

## PDF page 33

6.2 Model Results: XGBoost
Figure 12 demonstrates the impact of applying the XGBoost model to the Flushing
traffic simulation, showing predicted NOx levels after rerouting vehicles to mitigate
emissions. The visual comparison between this map and both the pre-model map (high
pollution levels) and the Random Forest Regressor results highlights the superior
performance of the XGBoost model in reducing pollution across the area.
32

## PDF page 34

- - Figure 12: NOx Levels AfterXGB Model
-
In the initial, pre-model simulation, a substantial number of pollution
hotspots—areas with elevated NOx concentrations—were present, marked by darker shades
of red. After applying the Random Forest Regressor model, there was a noticeable reduction
in these hotspots, signaling a positive impact on air quality. However, the XGBoost model,
as evidenced by the results in Figure 12, has gone a step further, reducing even more NOx
concentrations. The red circles on this map, which signify areas of higher emissions, are
significantly fewer and smaller compared to the earlier results.
This suggests that the XGBoost model was particularly effective in refining traffic
rerouting strategies, identifying more optimal paths that reduced congestion and pollution to
a greater degree than the Random Forest model. The cleaner, blue-dominant map indicates
that the XGBoost algorithm was able to predict and reroute vehicles with more precision,
distributing trafficmore evenly and avoiding the overburdening of high-emission zones.
Furthermore, the differences in the density and distribution of hotspots between the
models suggest that XGBoost may be better suited to managing traffic in complex urban
environments like Flushing, where pollution reduction requires careful consideration of
multiple, often competing, factors. These findings underscore the potential of more
advanced models like XGBoost to improve real-time pollution mitigation strategies by
minimizing the environmental impact of urban traffic.
6.3 Random Forest Regressor vs. XGBoost
In this subsection, we analyze the performance of two machine learning models,
Random Forest Regressor and XGBoost, in predicting and reducing emissions during
SUMO traffic simulations. The evaluation is based on the percentage drop in emissions for
key pollutants, as shown in Figure 13, and the distribution of emissions for both models,
alongside the original dataset, displayed in Figure 14.
33

## PDF page 35

- -Figure 13:ResultTable Summary
-
The table in Figure 13 provides a detailed comparison of the emissions reduction achieved
by both the Random Forest Regressor and XGBoost models across five pollutants: CO2,
CO, NOx, HC, and PMx. The percentage drop in emissions demonstrates that while both
models significantly reduced pollutants compared to the original emissions, XGBoost
consistently outperforms Random Forest inevery category:
❖ CO2: XGBoost achieved a 73.65% reduction, slightlyhigher than the 72%
reduction by Random Forest.
❖ CO: A 70.15% drop was seen with XGBoost, compared to63.99% with
Random Forest.
❖ NOx: XGBoost reduced NOx by 73.41%, while Random Forest managed
71.53%.
❖ HC: The reduction in HC emissions was 70.72% for XGBoost versus
65.31% for Random Forest.
34

## PDF page 36

❖ PMx: XGBoost reduced PMx emissions by 72.84%, exceeding Random
Forest's 70.39%.
These improvements, though seemingly incremental, showcase XGBoost's superior ability
to handle complex nonlinear relationships in the data. This makes it more effective in
practical, real-time trafficscenarios.
35

## PDF page 37

-
- -Figure 14:Post Simulation Emissions Log
Figure 14 displays histograms for each emission type, comparing the original dataset, the
Random Forest predictions, and the XGBoost predictions. These visualizations help to
illustrate how both models handle the distribution of emissions across the simulation:
36

## PDF page 38

❖ In all graphs (CO2, CO, NOx, HC, PMx), the original dataset (in green) has
a higher frequency of emissions concentrated in the lower ranges, with long tails
extending into higher emission levels.
❖ The Random Forest model (blue) significantly reduces the frequency of high
emissions, but stillexhibits a noticeable tail.
❖ XGBoost (red), on the other hand, further reduces the tailand shifts more of
the emissions towards the lower ranges, demonstrating its ability to better compress
emission distributions and reduce outliers.
Though the Random Forest Regressor performed well during training and testing with lower
Mean Squared Error (MSE), its real-time performance in the simulation lagged behind that
of XGBoost. The Random Forest model struggles to maintain accuracy in dynamic,
real-time conditions, where the relationship between traffic flow and emissions can vary
rapidly.
In contrast, XGBoost’s ability to optimize on gradients and handle the nonlinear nature of
emissions proves advantageous, making it more robust for practical applications in live
traffic simulations. The superior performance of XGBoost highlights its potential for
real-time air quality monitoring and trafficmanagement, providing both greater accuracy in
emission predictions and better overall reductions in pollutants across the board.
6.4 Further Analysis
Figures 15 and 16 present insightful visualizations comparing emissions data from
the original dataset and predictions from the Random Forest (RF) and XGBoost models
across multiple pollutants, including CO2, CO, NOx, HC, and PMx. In Figure 15, scatter
37

## PDF page 39

plots illustrate the relationship between original emissions and model predictions, offering a
clear view of how both models track with actual emission values. While the general trend
indicates reasonable alignment between the predicted and actual values, particularly in
lower emission ranges, deviations from the ideal diagonal line (representing perfect
prediction) become more pronounced at higher emission values. This trend is particularly
evident in CO2, where larger variances highlight challenges the models face in accurately
predicting emissions as they increase in magnitude. Despite these deviations, both RF and
XGBoost display consistent performance, though XGBoost shows a slight edge in certain
pollutants, particularly for PMx and NOx, where it more closely adheres to the ideal
prediction line.
38

## PDF page 40

-
- -Figure 15: Emission Data ScatterPlot
Figure 16 further explores model performance by plotting NOx emissions over time.
Here, the time series reveals that both models generally track the original NOx values quite
well, with XGBoost producing slightly smoother predictions, whereas Random Forest
captures more variability. This observation is especially evident around the 200,000 time
step, where a noticeable divergence occurs between the models before returning to a closer
alignment with the original emissions. The continuous overlap of predicted and actual
values over the span of time steps underscores the overall effectiveness of both models in
39

## PDF page 41

modeling NOx emissions, though subtle differences in how each model handles emission
spikes or troughs highlight their respective strengths and areas for improvement.
- - Figure 16: Comparison ofNOx Emissions
Given the superior performance of XGBoost, particularly in its ability to handle
emission spikes and closely follow the ideal predictions, it would be an ideal candidate for
real-time deployment across all pollutants. XGBoost has proven to be highly effective in
reducing emissions and implementing traffic mitigation strategies, largely due to its faster
convergence and ability to better capture complex patterns in the data. Therefore, for
optimal results in real-time emission reduction and traffic management scenarios, the
XGBoost model would be recommended over Random Forest, providing the highest levels
of emission reduction and trafficflow improvements.
40

## PDF page 42

7. Discussion
From our findings, it is evident that the XGBoost model has consistently outperformed
the Random Forest model in predicting emission levels, making it the superior choice for
real-time emission reduction strategies in densely populated urban environments. The
performance of XGBoost, as highlighted in our comparison, demonstrates its ability to not only
closely mirror actual emission levels but also handle spikes in pollutant concentrations more
effectively than its counterpart. This enhanced prediction capability positions XGBoost as a
valuable tool for mitigating traffic-related emissions, a crucial factor in improving air quality in
citieswhere vehicle density and pollution levels are significantly high.
The implications of these results extend beyond model accuracy. By reducing emission
levels, especially in pollution hotspots, the XGBoost model can contribute meaningfully to
environmental sustainability efforts. The ability to dynamically reroute traffic and optimize
vehicle movement using this model can play a pivotal role in reducing the overall carbon
footprint of transportation systems. As cities worldwide continue to combat the adverse effects of
air pollution, implementing such data-driven solutions will be instrumental in shaping cleaner
and healthier urban environments. The model’s effectiveness in real-time scenarios reinforces its
potential for integration into smart city infrastructures, where reducing emissions and enhancing
trafficmanagement are both critical goals.
By leveraging the predictive power of XGBoost, cities can better manage their traffic
systems to not only improve the flow of vehicles but also significantly cut down on harmful
pollutants, directly contributing to long-term environmental sustainability and public health.
7.1 Limitations of Scope: Focusing Solely on Cars
In this study, we focused exclusively on emissions generated by cars, which allowed
us to develop a focused, manageable model for emission reduction in urban environments.
However, itis important to acknowledge that cars represent only one component of the
41

## PDF page 43

broader spectrum of traffic-related pollutants. Other vehicle types such as trucks, buses,
motorcycles, and electric vehicles also contribute significantly to emissions, each with
distinct driving patterns and emission profiles that were not accounted for in this study.
Including these vehicles would provide a more comprehensive view of urban pollution, but
due to the limitations of our dataset and the scope of this project, we were unable to
incorporate these factors.
Beyond vehicle variety, there are numerous other critical factors that influence road
emissions, such as road conditions, weather, and driving behaviors, which were also not
modeled in our analysis. Factors like traffic congestion, road surface quality, and varying
driving speeds can have significant impacts on the level of emissions produced, but they
were outside the scope of our current work. Furthermore, external influences such as
construction activities or the presence of pedestrian zones could play a role in determining
traffic flow and emissions, yet these too were not considered due to limitations in data
collection and simulation capabilities.
Future iterations of this study could benefit greatly from expanding the scope to
include these additional vehicle types and environmental factors. Incorporating a more
diverse set of variables would not only enhance the accuracy of emissions predictions but
also provide a more realistic framework for developing mitigation strategies. This would be
especially beneficial for cities aiming to implement holistic environmental policies and
trafficmanagement solutions that address all contributing factors to urban pollution.
42

## PDF page 44

7.2 Future Work and Broader Impact
- -Figure 17: The Grater Map ofFlushing ,NY
Looking ahead, our research aims to address the limitations discussed earlier and
broaden the scope of our work to include a wider range of variables and real-world
conditions. We recognize the importance of expanding our model beyond passenger cars to
encompass other vehicle types such as trucks, buses, and motorcycles, all of which
contribute significantly to urban pollution. Additionally, we plan to incorporate factors such
as weather, road conditions, and driving behavior into our models, which will allow for a
more comprehensive understanding of traffic emissions and their impact on urban air
quality.
Our ultimate goal is to refine and develop this model to the point where it can be
applied in real-world scenarios. By doing so, we aspire to contribute to the environmental
sustainability efforts not just in academic settings but in practical, real-life applications. One
of the major ambitions of our future work is to implement this model in densely populated
areas such as Flushing, New York City, and other metropolitan regions across the globe,
43

## PDF page 45

where the reduction of air pollution is crucial for improving public health and environmental
quality.
By integrating machine learning models like XGBoost with real-time data, we hope
to create a solution that will help cities manage traffic and emissions more effectively,
leading to cleaner air and healthier living conditions for millions of people. Our long-term
vision is to provide a framework that can be adopted by city planners and environmental
agencies, enabling cities to achieve their sustainability goals through data-driven
decision-making.
We are committed to continuing this line of research with environmental
sustainability as a core focus, and we believe that our work will serve as a stepping stone
toward making urban areas more livable and environmentally friendly. By building upon the
foundation we have established, we aim to drive meaningful change and help cities around
the world tackle one of the most pressing challenges of our time, air pollution.
8. Conclusion
In conclusion, thisresearch has been a pivotal experience for us as Data Science students,
providing an opportunity to apply theoretical knowledge to a complex real-world challenge. Our
work centered on addressing traffic-induced air pollution, a critical issue in densely populated
urban areas. By using SUMO simulations and machine learning techniques, we were able to
analyze, predict, and propose effective solutions to reduce harmful emissions. Through our
experimentation, we successfully integrated various stages of the data science process—ranging
from data collection and preprocessing to model selection, evaluation, and performance analysis.
One of the major takeaways from this project was the superior performance of the
XGBoost model in reducing emissions. Our findings demonstrate that XGBoost, with its
44

## PDF page 46

advanced boosting capabilities, was able to significantly outperform other models such as
Random Forest, proving itself to be the most effective in optimizing rerouting strategies and
lowering pollution levels. This is especially important when considering its application in
densely populated cities like New York, where reducing air pollution is critical for improving
public health and environmental sustainability. The results suggest that XGBoost could be
implemented in real-time traffic management systems to reduce congestion and mitigate air
pollution in urban settings.
Beyond the technical findings, this project reinforced the importance of data-driven
solutions in tackling global issues such as environmental sustainability. The experiment allowed
us to explore how data science can be applied not just for insights but also to drive actionable
solutions, emphasizing the intersection between technology and sustainability. We also
recognized the limitations of our study, including the focus on only one type of vehicle and the
exclusion of additional factors like weather or road conditions. Addressing these limitations
would be essential in further refining our model.
This research has provided us with practical experience in navigating the entire data
science workflow, from problem identification to the implementation of machine learning
models and the interpretation of results. It has enhanced our technical skills and deepened our
understanding of the ethical and societal impacts of our work, particularly as we focus on
sustainability. Through this project, we have gained the confidence to tackle complex datasets
and leverage machine learning in ways that can lead to tangible improvements in society.
Overall, this experiment has allowed us to realize the potential of data science in driving
meaningful change, particularly in environmental conservation efforts. As we move forward, this
experience has strengthened our resolve to continue contributing to global sustainability through
data-driven approaches. The knowledge we’ve acquired, paired with the understanding of
real-world implications, positions us to continue making significant contributions to the field of
data science and beyond.
45

## PDF page 47

8.1 Special Thanks
We would like to extend our deepest appreciation to Professor Huang for her
unwavering guidance and support throughout this research journey. As our supervisor, she
provided invaluable insights and thoughtful feedback that helped us navigate the
complexities of the project. Her encouragement to challenge ourselves intellectually and
think critically has been instrumental in the success of this research.
Throughout the semesters, Professor Huang has been an exemplary mentor, not only
imparting technical knowledge but also fostering a holistic understanding of what itmeans
to be a responsible and effective data scientist. Her dedication to teaching and her passion
for the field have inspired us to strive for excellence in both our academic pursuits and
professional careers. This project, and our growth as data scientists, would not have been
possible without her mentorship.
Thank you, Professor Huang, for teaching us the skills, ethics, and mindset required
to make meaningful contributions to the field of data science.
46

## PDF page 48

9. References
Work Cited
SUMO. “Interfacing TraCI from Python -SUMO Documentation.” Eclipse SUMO -Simulation
of Urban MObility, 6 August 2024,
https://sumo.dlr.de/docs/TraCI/Interfacing_TraCI_from_Python.html. Accessed 14
October 2024.
Jiang, D., et al.(2022). "A Bibliometric Study of Machine Learning Applications in Air
Pollution Research." Environmental Monitoring and Assessment, 192(1), 101.
Lin, H., et al.(2020). "Predicting Urban Traffic Emissions using SUMO and Taxi Trajectory
Data." Transportation Research Part D: Transport and Environment, 85, 102416.
Javid, A., et al.(2022). "Traffic Signal Optimization for Air Pollution Control in Urban Areas."
Sustainable Cities and Society, 72, 103045.
Dong, X., et al.(2021). "Dynamic Vehicle Rerouting for Urban Pollution Reduction Using
Reinforcement Learning." Journal of Intelligent Transportation Systems, 25(3), 235-251.
47
