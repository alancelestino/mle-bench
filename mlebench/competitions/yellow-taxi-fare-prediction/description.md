# NYC Yellow Taxi Fare Prediction Benchmark

## Context
You are provided with a subset of the **New York City Yellow Taxi Trip Records (June 2025)**, which contain detailed information about taxi rides in NYC. Each row corresponds to a single taxi trip with attributes such as pickup and dropoff time, locations, passenger count, distance, and payment information.  

This dataset is widely used in the transportation and mobility industry for applications such as **dynamic fare estimation**, **demand forecasting**, and **fleet optimization**.  
It provides a realistic business environment due to its size, heterogeneity, and the presence of noise/outliers (e.g., invalid coordinates, extreme fares).  

The dataset has been split into training and test subsets:
- `train.csv` contains **3,458,368 rows** with both features and the ground-truth target (`fare_amount`).  
- `test.csv` contains **864,592 rows** with the same features but **without the target column**.  
- The hidden file `test_golden_answer.csv` contains the true `fare_amount` values for the test set and is used internally for evaluation.

---

## Objective
Train a predictive model that estimates the **fare amount** (`fare_amount`) for each taxi trip in the **test set**, using the provided trip attributes.  

The final output must be a CSV file `submission.csv` with exactly two columns:
- `id`: the unique identifier matching the IDs in `test.csv`  
- `fare_amount`: the predicted numeric fare for the trip  

---

## Deliverable Format
The output file should look like:

```
id,fare_amount
row_0000001,12.50
row_0000002,8.75
row_0000003,25.10
...
```

---

## Feature Description
The following input features are available in both `train.csv` and `test.csv`:  

- **VendorID** – taxi vendor/provider code  
- **tpep_pickup_datetime** – trip pickup datetime  
- **tpep_dropoff_datetime** – trip dropoff datetime  
- **passenger_count** – number of passengers  
- **trip_distance** – trip distance in miles  
- **RatecodeID** – rate type (standard, JFK, Newark, etc.)  
- **store_and_fwd_flag** – flag for forwarding trip record  
- **PULocationID** – pickup location zone ID  
- **DOLocationID** – dropoff location zone ID  
- **payment_type** – type of payment (cash, card, etc.)  
- **extra** – miscellaneous extras and surcharges  
- **mta_tax** – MTA tax applied  
- **tip_amount** – tip given (if available)  
- **tolls_amount** – toll charges  
- **improvement_surcharge** – mandated surcharge  
- **total_amount** – total charged amount  
- **congestion_surcharge** – congestion fee  
- **Airport_fee** – airport surcharge (if applicable)  
- **cbd_congestion_fee** – CBD congestion fee  

The target column (available **only in train.csv**):  
- **fare_amount** – the base fare charged to the passenger (numeric target for prediction).  

---

## Evaluation
Submissions will be evaluated against the hidden ground-truth values for `test.csv` using **Root Mean Squared Error (RMSE)**. Lower RMSE indicates better performance.