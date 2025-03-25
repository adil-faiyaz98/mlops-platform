# training/training_pipeline.py
# This file orchestrates the whole training process

import os
import pandas as pd
from training.features.feature_engineering import apply_feature_engineering
from training.models.train_model import train_and_save_model
from training.metrics.evaluation import calculate_metrics
from training.experiments.experiment_tracker import start_experiment, log_metric, log_parameter, end_experiment, log_model
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

# Define paths (Adjust these based on your project structure)
DATA_PATH = "data/training_data.csv" # Path to your training data
MODEL_OUTPUT_PATH = "models/my_model.joblib" # Where to save the trained model
EXPERIMENT_NAME = "MyTrainingPipeline"

def main():
    """
    Main function to orchestrate the training pipeline.
    """
    try:
        # 1. Start experiment tracking
        start_experiment(EXPERIMENT_NAME)

        # 2. Load data
        print(f"Loading data from {DATA_PATH}")
        data = pd.read_csv(DATA_PATH)

        # 3. Feature Engineering
        print("Applying feature engineering...")
        data = apply_feature_engineering(data)

        # 4. Prepare data for training
        # Assuming the last column is the target variable
        X = data.iloc[:, :-1]
        y = data.iloc[:, -1]

        # Split into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # 5. Train the model
        print("Training the model...")
        model = LogisticRegression(solver='liblinear', random_state=42)  # Example model
        model.fit(X_train, y_train)
        log_parameter("model_type", "LogisticRegression")  # Log to MLflow

        # 6. Evaluate the model
        print("Evaluating the model...")
        y_pred = model.predict(X_test)
        metrics = calculate_metrics(y_test, y_pred)
        print(f"Metrics: {metrics}")

        # 7. Log metrics to experiment tracker (MLflow)
        for metric_name, metric_value in metrics.items():
            log_metric(metric_name, metric_value)

        # 8. Save the trained model
        print(f"Saving model to {MODEL_OUTPUT_PATH}")
        os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)  # Ensure directory exists
        # joblib.dump(model, MODEL_OUTPUT_PATH)
        log_model(model, "model") # Use MLflow to log the model

        # 9. End experiment tracking
        end_experiment()

        print("Training pipeline completed successfully!")

    except Exception as e:
        print(f"Error in training pipeline: {e}")
    finally:
        print("Done.")

if __name__ == "__main__":
    main()