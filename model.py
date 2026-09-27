"""
model.py - CNN Model for Heart Disease Prediction using PyTorch
Handles dataset loading, preprocessing, model training, saving, loading, and prediction.
"""

import os
import numpy as np
import pandas as pd
import json
import pickle
import warnings

warnings.filterwarnings("ignore")

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(_BASE_DIR, "dataset", "heart.csv")
MODEL_PATH = os.path.join(_BASE_DIR, "saved_model", "heart_cnn_model.pth")
SCALER_PATH = os.path.join(_BASE_DIR, "saved_model", "scaler.pkl")
HISTORY_PATH = os.path.join(_BASE_DIR, "saved_model", "training_history.json")
METRICS_PATH = os.path.join(_BASE_DIR, "saved_model", "metrics.json")

FEATURE_COLS = ["age", "sex", "cp", "trestbps", "chol", "fbs",
                "restecg", "thalach", "exang", "oldpeak", "slope", "ca", "thal"]


def dataset_exists() -> bool:
    return os.path.exists(DATASET_PATH)


def model_exists() -> bool:
    return os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH)


def load_dataset() -> tuple:
    """Load and preprocess the heart disease dataset."""
    df = pd.read_csv(DATASET_PATH)

    # Standardize column names
    df.columns = [c.lower().strip() for c in df.columns]

    # Ensure target column exists
    if "target" not in df.columns and "condition" in df.columns:
        df.rename(columns={"condition": "target"}, inplace=True)
    elif "target" not in df.columns:
        raise ValueError("Dataset must have a 'target' column (0=No Disease, 1=Disease).")

    # Binarize target (some datasets use values > 1 for disease)
    df["target"] = (df["target"] > 0).astype(int)

    # Keep only relevant features
    available_cols = [c for c in FEATURE_COLS if c in df.columns]
    df = df[available_cols + ["target"]].copy()

    # Handle missing values
    df.dropna(inplace=True)

    return df, available_cols


# ─── PyTorch 1D CNN Model Definition ───

def _build_torch_model(n_features: int):
    """Build and return a PyTorch 1D CNN model for binary classification."""
    import torch
    import torch.nn as nn

    class HeartCNN(nn.Module):
        def __init__(self, n_features):
            super().__init__()
            self.conv_block1 = nn.Sequential(
                nn.Conv1d(1, 64, kernel_size=3, padding=1),
                nn.BatchNorm1d(64),
                nn.ReLU(),
            )
            self.conv_block2 = nn.Sequential(
                nn.Conv1d(64, 128, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.MaxPool1d(kernel_size=2, stride=2),
                nn.Dropout(0.25),
            )
            self.conv_block3 = nn.Sequential(
                nn.Conv1d(128, 64, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.Dropout(0.25),
            )

            # Compute flattened size
            # Input: (batch, 1, n_features) -> after pool of 2: (batch, 128, n_features//2)
            flat_dim = 64 * max(1, n_features // 2)

            self.fc = nn.Sequential(
                nn.Flatten(),
                nn.Linear(flat_dim, 128),
                nn.ReLU(),
                nn.Dropout(0.5),
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, 1),
                nn.Sigmoid(),
            )

        def forward(self, x):
            x = self.conv_block1(x)
            x = self.conv_block2(x)
            x = self.conv_block3(x)
            x = self.fc(x)
            return x

    return HeartCNN(n_features)


def train_model():
    """
    Train the 1D CNN model on the heart disease dataset using PyTorch.
    Returns (history_dict, test_accuracy, test_loss).
    """
    import torch
    import torch.nn as nn
    from torch.utils.data import TensorDataset, DataLoader
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    df, available_cols = load_dataset()
    X = df[available_cols].values.astype(np.float32)
    y = df["target"].values.astype(np.float32)

    # Train-test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Normalize features
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train).astype(np.float32)
    X_test = scaler.transform(X_test).astype(np.float32)

    # Reshape for Conv1D: (samples, 1, n_features) — channels first
    X_train_t = torch.tensor(X_train[:, np.newaxis, :])   # (N, 1, F)
    X_test_t  = torch.tensor(X_test[:, np.newaxis, :])
    y_train_t = torch.tensor(y_train[:, np.newaxis])
    y_test_t  = torch.tensor(y_test[:, np.newaxis])

    n_features = X_train.shape[1]

    model = _build_torch_model(n_features)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.BCELoss()
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5
    )

    train_ds = TensorDataset(X_train_t, y_train_t)
    train_dl = DataLoader(train_ds, batch_size=16, shuffle=True)

    history = {"accuracy": [], "val_accuracy": [], "loss": [], "val_loss": []}

    best_val_loss = float("inf")
    patience_counter = 0
    PATIENCE = 10
    EPOCHS = 50
    best_state = None

    model.train()
    for epoch in range(EPOCHS):
        # ── Training ──
        model.train()
        epoch_loss = 0.0
        correct = 0
        total = 0
        for xb, yb in train_dl:
            optimizer.zero_grad()
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * len(xb)
            predicted = (pred >= 0.5).float()
            correct += (predicted == yb).sum().item()
            total += len(yb)

        train_loss = epoch_loss / len(X_train)
        train_acc = correct / total

        # ── Validation ──
        model.eval()
        with torch.no_grad():
            val_pred = model(X_test_t)
            val_loss = criterion(val_pred, y_test_t).item()
            val_acc = ((val_pred >= 0.5).float() == y_test_t).float().mean().item()

        scheduler.step(val_loss)

        history["accuracy"].append(round(train_acc, 4))
        history["val_accuracy"].append(round(val_acc, 4))
        history["loss"].append(round(train_loss, 4))
        history["val_loss"].append(round(val_loss, 4))

        print(f"Epoch {epoch+1:3d}/{EPOCHS} | "
              f"loss: {train_loss:.4f} acc: {train_acc:.4f} | "
              f"val_loss: {val_loss:.4f} val_acc: {val_acc:.4f}")

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                print(f"Early stopping at epoch {epoch+1}.")
                break

    # Restore best weights
    if best_state:
        model.load_state_dict(best_state)

    # Final evaluation
    model.eval()
    with torch.no_grad():
        test_pred = model(X_test_t)
        test_loss = criterion(test_pred, y_test_t).item()
        test_acc = ((test_pred >= 0.5).float() == y_test_t).float().mean().item()

    # Save model and scaler
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    # Save as a state dict + architecture info
    torch.save({
        "state_dict": model.state_dict(),
        "n_features": n_features,
    }, MODEL_PATH)

    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f)

    metrics = {
        "test_accuracy": round(float(test_acc) * 100, 2),
        "test_loss": round(float(test_loss), 4),
        "train_samples": int(X_train.shape[0]),
        "test_samples": int(X_test.shape[0]),
        "features_used": available_cols,
        "epochs_trained": len(history["accuracy"]),
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f)

    return history, test_acc, test_loss


def load_model_and_scaler():
    """Load the trained CNN model and scaler from disk."""
    import torch

    checkpoint = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    n_features = checkpoint["n_features"]
    model = _build_torch_model(n_features)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)

    return model, scaler


def get_training_history() -> dict:
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH) as f:
            return json.load(f)
    return {}


def get_metrics() -> dict:
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH) as f:
            return json.load(f)
    return {}


def predict(input_values: list) -> tuple:
    """
    Make a prediction from raw user input.

    Args:
        input_values: list of 13 feature values in order of FEATURE_COLS

    Returns:
        (prediction_label: str, probability: float, risk_level: str)
    """
    import torch

    model, scaler = load_model_and_scaler()

    input_array = np.array(input_values, dtype=np.float32).reshape(1, -1)
    input_scaled = scaler.transform(input_array).astype(np.float32)
    input_tensor = torch.tensor(input_scaled[:, np.newaxis, :])  # (1, 1, F)

    with torch.no_grad():
        prob = float(model(input_tensor)[0][0])

    if prob >= 0.5:
        label = "High Risk of Heart Disease"
        risk_level = "high"
    else:
        label = "No Heart Disease"
        risk_level = "low"

    return label, round(prob * 100, 2), risk_level
