# training/experiments/experiment_tracker.py

import mlflow  # You'll need to install mlflow: pip install mlflow

def start_experiment(experiment_name):
    """
    Starts an MLflow experiment.

    Args:
        experiment_name (str): The name of the experiment.
    """
    try:
        mlflow.set_experiment(experiment_name)
        mlflow.start_run()
        print(f"MLflow experiment '{experiment_name}' started.")
    except Exception as e:
        print(f"Error starting MLflow experiment: {e}")
        raise

def log_metric(key, value):
    """
    Logs a metric to MLflow.

    Args:
        key (str): The name of the metric.
        value (float): The value of the metric.
    """
    try:
        mlflow.log_metric(key, value)
    except Exception as e:
        print(f"Error logging metric to MLflow: {e}")

def log_parameter(key, value):
    """
    Logs a parameter to MLflow.

    Args:
        key (str): The name of the parameter.
        value (any): The value of the parameter.
    """
    try:
        mlflow.log_param(key, value)
    except Exception as e:
        print(f"Error logging parameter to MLflow: {e}")

def log_model(model, artifact_path):
    """Logs the trained model as an artifact to MLflow"""
    try:
        mlflow.sklearn.log_model(model, artifact_path=artifact_path)
    except Exception as e:
        print(f"Error logging model to MLflow: {e}")


def end_experiment():
    """
    Ends the current MLflow experiment run.
    """
    try:
        mlflow.end_run()
        print("MLflow experiment run ended.")
    except Exception as e:
        print(f"Error ending MLflow experiment: {e}")

if __name__ == '__main__':
    # Example Usage
    EXPERIMENT_NAME = "MyTrainingExperiment"
    start_experiment(EXPERIMENT_NAME)

    # Log parameters
    log_parameter("learning_rate", 0.01)
    log_parameter("batch_size", 32)

    # Simulate metric calculation
    accuracy = 0.85
    log_metric("accuracy", accuracy)

    # Simulate saving a model
    # (In a real scenario, you'd save the model object itself)

    end_experiment()