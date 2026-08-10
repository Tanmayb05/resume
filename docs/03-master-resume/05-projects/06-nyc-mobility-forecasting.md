### **NYC Mobility Forecasting | ML-Driven Taxi/Rideshare Demand Prediction System**
**July 2026**

**Tech Stack:** Python, PySpark, Apache Spark, Delta Lake, Scikit-learn, Machine Learning, FastAPI, SQL, PostgreSQL, Redis, Docker, Oracle Cloud, React, REST API, CI/CD

**Context:** End-to-end machine learning system forecasting NYC taxi/FHV demand at zone/hour level using NYC TLC trip data. Ingests transportation, weather, and geospatial data through a Spark-based medallion (bronze/silver/gold) pipeline, trains and deploys a production ML model, and serves real-time predictions through a REST API and web dashboard.

- Built machine learning system forecasting NYC taxi/rideshare demand across 263 zones using Python, PySpark, Delta Lake, and scikit-learn, processing trip and weather data into a 2.3M-row hourly demand dataset
- Designed two-stage (classification + regression) Poisson hurdle model predicting trip demand and surge risk, improving forecast accuracy (weighted MAPE 18.77%→16.52%) and cutting prediction error (RMSE) by 43%, (MAE) by 53% over baseline Random Forest
- Built RESTful API (Python, FastAPI) serving real-time demand predictions to a React/map-based dashboard, integrated with PostgreSQL and Redis caching, containerized with Docker, and architected for free-tier cloud deployment (Oracle Cloud)
