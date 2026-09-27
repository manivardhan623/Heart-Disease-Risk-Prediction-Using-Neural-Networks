# Heart Disease Prediction Using CNN

An end-to-end AI web application that predicts heart disease risk using a 1D Convolutional Neural Network (CNN) built with PyTorch, served via a Flask web application.

---

## 📁 Project Structure

```
pdnc project/
│
├── app.py                   # Main Flask application (routes, session, API)
├── model.py                 # CNN model: build, train, save, predict
├── auth.py                  # Authentication: signup, login, password hashing
├── requirements.txt         # Python dependencies
│
├── dataset/
│   └── heart.csv            # UCI Heart Disease dataset (replace with full version)
│
├── saved_model/             # Created automatically after training
│   ├── heart_cnn_model.pth  # Saved PyTorch model
│   ├── scaler.pkl           # Saved StandardScaler
│   ├── training_history.json
│   └── metrics.json
│
├── templates/
│   ├── base.html            # Base layout
│   ├── login.html           # Login page
│   ├── signup.html          # Signup page
│   └── dashboard.html       # Main dashboard
│
└── static/
    ├── css/style.css        # All styles (dark glassmorphism theme)
    └── js/main.js           # Charts, prediction fetch, UX logic
```

---

## 🚀 Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Replace the dataset
Download the full **UCI Heart Disease dataset** from Kaggle:
> https://www.kaggle.com/datasets/ronitf/heart-disease-uci

Place the downloaded `heart.csv` in the `dataset/` folder.
A dataset is already included so the app works out-of-the-box.

### 3. Run the app
```bash
python app.py
```

Then open your browser at: **http://127.0.0.1:5000**

For deployment, set a strong secret key before starting the app:
```bash
set FLASK_SECRET_KEY=replace-with-a-long-random-value
python app.py
```

---

## 🧠 CNN Model Architecture

```
Input (13 features, reshaped to 13×1 for a PyTorch 1D CNN)
  └─ Conv1D(64, kernel=3, ReLU) + BatchNorm
  └─ Conv1D(128, kernel=3, ReLU) + MaxPool + Dropout(0.25)
  └─ Conv1D(64, kernel=3, ReLU) + MaxPool + Dropout(0.25)
  └─ Flatten
  └─ Dense(128, ReLU) + Dropout(0.5)
  └─ Dense(64, ReLU)
  └─ Dense(1, Sigmoid)  ← Binary output

Optimizer: Adam (lr=0.001)
Loss:      Binary Crossentropy
Metrics:   Accuracy
Epochs:    Up to 50 (EarlyStopping with patience=10)
Batch:     16
Split:     80% train / 20% test
```

---

## 🔐 Authentication

- **Signup**: Username + Email + Password (hashed with SHA-256 + salt)
- **Login**: Validates credentials against SQLite database (`users.db`)
- **Session**: Flask session-based, protected with `@login_required`
- **Logout**: Clears session completely

---

## 📊 Features

| Feature | Details |
|---------|---------|
| Auth System | Signup / Login / Logout with hashed passwords |
| Prediction | 13 clinical inputs → CNN → Risk assessment |
| Dataset Upload | Drag & drop or browse to upload heart.csv |
| Model Training | One-click CNN training with progress feedback |
| Visualizations | Accuracy & Loss curves via Chart.js |
| Metrics Display | Test accuracy, loss, sample counts |
| Info Section | Heart disease facts, risk factors, disclaimer |
| Responsive UI | Works on desktop, tablet, and mobile |

---

## ⚠️ Disclaimer

This tool is for **educational and research purposes only**.  
It is **not** a medical device and should **not** replace professional medical advice.
