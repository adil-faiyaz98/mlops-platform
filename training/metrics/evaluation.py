# training/metrics/evaluation.py

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

def calculate_metrics(y_true, y_pred):
    """
    Calculates common classification metrics.

    Args:
        y_true (list or array): True labels.
        y_pred (list or array): Predicted labels.

    Returns:
        dict: A dictionary of calculated metrics.
    """
    try:
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, zero_division=0),  # Handle potential division by zero
            'recall': recall_score(y_true, y_pred, zero_division=0),
            'f1_score': f1_score(y_true, y_pred, zero_division=0)
        }
        return metrics
    except Exception as e:
        print(f"Error calculating metrics: {e}")
        raise


if __name__ == '__main__':
    # Example Usage
    y_true = [0, 1, 1, 0, 1]
    y_pred = [0, 1, 0, 0, 1]

    metrics = calculate_metrics(y_true, y_pred)
    print(metrics)