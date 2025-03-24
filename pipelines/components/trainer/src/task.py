# /project_root/pipelines/components/trainer/src/task.py
from kfp.v2 import dsl
from kfp.v2.dsl import (
    component,
    Input,
    Output,
    Artifact,
    Model,
    HTML,
    Metrics,
    ClassificationMetrics,
)
from typing import NamedTuple, Dict, List
@component(
    packages_to_install=["tensorflow", "pandas","scikit-learn"],
    base_image="python:3.9", #For example
)
def train_model(
    train_path: str,
    validation_path: str,
    epochs: int,
    model: Output[Model], # Model Name in a TF SavedModel Format.
    metrics: Output[ClassificationMetrics]
) -> NamedTuple(
    "output",
    [
        ("model_report", str), #Report
        ("testing_set", str),
        ("performance_report", HTML), # HTML
    ],
):
  """
  Train the model, load the model, and save metrics for future use.
  Returns the location of the test location
  """
  import pandas as pd
  import tensorflow as tf
  tf.keras.utils.set_random_seed(1)
  tf.config.experimental.enable_op_determinism()
  from sklearn.model_selection import train_test_split
  from sklearn.preprocessing import StandardScaler
  from sklearn.linear_model import LogisticRegression

  from sklearn.metrics import classification_report, confusion_matrix
  import json

  #Loads
  train_df = pd.read_csv(train_path) # Train
  valid_df = pd.read_csv(validation_path) # Test

  #Data preperation
  FEATURE_NAMES = ["feature1","feature2","feature3"] # Columns
  LABEL = "target" # Target

  X_train = train_df[FEATURE_NAMES].values #Feature Data
  y_train = train_df[LABEL].values #Target
  X_test = valid_df[FEATURE_NAMES].values
  y_test = valid_df[LABEL].values

  # Scale the data.
  scaler = StandardScaler() # Scaler Data
  X_train = scaler.fit_transform(X_train)
  X_test = scaler.transform(X_test)

  # Train the model
  logistic_model = LogisticRegression() #Model
  logistic_model.fit(X_train,y_train) #Training model

  # Evaluate the model
  y_pred = logistic_model.predict(X_test)
  report = classification_report(y_test, y_pred, output_dict = True) #Classification Report
  metrics_report = classification_report(y_test, y_pred)

  #Testing dataset
  testing_data_subset_uri = "testset.csv" #File name
  valid_df.to_csv(testing_data_subset_uri, index=False) #Transform

  #Load Metric.

  for class_name in report.keys():
    if class_name in ["accuracy", "macro avg", "weighted avg"]:
      continue #Remove
    metrics.log_confusion_matrix(
          [str(i) for i in valid_df[LABEL].unique().tolist()], #List of string in Test Set.
          confusion_matrix(y_test, y_pred)
    )
    break

  metrics.log_classification_report(report) #Output as JSON

  # Model Save
  model_path = os.path.join(model.path, "model.joblib") # Where to save model.
  tf.keras.models.save_model(logistic_model, model_path) # Saving TF

  metadata = {
      'outputs' : 'metrics.dataset_fraction_columns_with_missing_values.json, metrics.skew_histogram.json',
    }

  with open("output.json", 'w') as outfile:
    json.dump(metadata, outfile, indent=4)

  #Output Values for this training job
  return (model_report, testing_data_subset_uri, dsl.HTML(metrics_report))