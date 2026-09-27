"""
app.py - Main Flask Application for Heart Disease Prediction Using CNN
Routes: login, signup, logout, Google OAuth, dashboard, predict, train, charts API
"""

import os
import json
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from authlib.integrations.flask_client import OAuth
import auth
import model as mdl

# ─── App configuration ───
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(_BASE_DIR, "templates"),
            static_folder=os.path.join(_BASE_DIR, "static"))
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ─── Google OAuth configuration ───
# To enable real Google sign-in:
#   1. Go to https://console.cloud.google.com/
#   2. Create a project → Enable "Google People API" or "Google Identity"
#   3. Create OAuth 2.0 credentials (Web Application)
#   4. Add http://127.0.0.1:5000/google/callback to Authorized Redirect URIs
#   5. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET below
GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID",     "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_OAUTH_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

oauth = OAuth(app)
if GOOGLE_OAUTH_ENABLED:
    google = oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# ─── Initialize DB on startup ───
auth.init_db()


# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Both username and password are required.", "error")
            return render_template("login.html", google_enabled=GOOGLE_OAUTH_ENABLED)

        success, message, user_data = auth.login_user(username, password)
        if success:
            session["user"] = {
                "id": user_data["id"],
                "username": user_data["username"],
                "email":    user_data["email"],
            }
            flash(f"Welcome back, {user_data['username']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash(message, "error")

    return render_template("login.html", google_enabled=GOOGLE_OAUTH_ENABLED)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username         = request.form.get("username", "").strip()
        email            = request.form.get("email", "").strip()
        password         = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("signup.html", google_enabled=GOOGLE_OAUTH_ENABLED)

        success, message = auth.signup_user(username, email, password)
        if success:
            flash(message, "success")
            return redirect(url_for("login"))
        else:
            flash(message, "error")

    return render_template("signup.html", google_enabled=GOOGLE_OAUTH_ENABLED)


@app.route("/logout")
def logout():
    username = session.get("user", {}).get("username", "User")
    session.clear()
    flash(f"You've been logged out, {username}.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────────────────────
# GOOGLE OAUTH ROUTES
# ─────────────────────────────────────────────

@app.route("/google/login")
def google_login():
    if not GOOGLE_OAUTH_ENABLED:
        flash("Google sign-in is not configured yet. See README for setup instructions.", "warning")
        return redirect(url_for("login"))
    redirect_uri = url_for("google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route("/google/callback")
def google_callback():
    if not GOOGLE_OAUTH_ENABLED:
        flash("Google sign-in is not configured.", "error")
        return redirect(url_for("login"))

    try:
        token = google.authorize_access_token()
        user_info = token.get("userinfo")
        if not user_info:
            flash("Could not retrieve user info from Google.", "error")
            return redirect(url_for("login"))

        email    = user_info.get("email", "").lower()
        name     = user_info.get("name", "")
        # Build a safe username from the Google name
        username = name.replace(" ", "_").lower()[:20] or email.split("@")[0]

        # Auto-register or retrieve existing google user
        success, message = auth.signup_user(
            username=username,
            email=email,
            password=user_info.get("sub", "google_oauth_user")  # use sub as pseudo-password
        )
        # If signup fails because user exists (email duplicate), that's fine — try login
        if not success and "already registered" not in message.lower() and "already exists" not in message.lower():
            flash(f"Google sign-in error: {message}", "error")
            return redirect(url_for("login"))

        # Retrieve user from DB by email
        user_data = auth.get_user_by_email(email)
        if user_data:
            session["user"] = {
                "id":       user_data["id"],
                "username": user_data["username"],
                "email":    user_data["email"],
            }
            flash(f"Welcome, {user_data['username']}! Signed in with Google.", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Could not log in with Google. Please sign up manually.", "error")
            return redirect(url_for("login"))

    except Exception as e:
        flash(f"Google sign-in failed: {str(e)}", "error")
        return redirect(url_for("login"))


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.route("/dashboard")
@auth.login_required
def dashboard():
    dataset_ok = mdl.dataset_exists()
    model_ok   = mdl.model_exists()
    metrics    = mdl.get_metrics() if model_ok else {}
    history    = mdl.get_training_history() if model_ok else {}

    return render_template(
        "dashboard.html",
        user=session["user"],
        dataset_ok=dataset_ok,
        model_ok=model_ok,
        metrics=metrics,
        history=history,
    )


# ─────────────────────────────────────────────
# TRAIN MODEL
# ─────────────────────────────────────────────

@app.route("/train", methods=["POST"])
@auth.login_required
def train():
    if not mdl.dataset_exists():
        flash("Dataset not found. Please upload heart.csv to the dataset/ folder.", "error")
        return redirect(url_for("dashboard"))

    try:
        history_dict, test_acc, test_loss = mdl.train_model()
        flash(
            f"✓ Model trained! Test Accuracy: {test_acc * 100:.2f}%  |  Loss: {test_loss:.4f}",
            "success"
        )
    except Exception as e:
        flash(f"Training failed: {str(e)}", "error")

    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────
# PREDICTION
# ─────────────────────────────────────────────

@app.route("/predict", methods=["POST"])
@auth.login_required
def predict():
    if not mdl.model_exists():
        return jsonify({"error": "Model not trained yet. Please train the model first."}), 400

    field_names = ["age", "sex", "cp", "trestbps", "chol", "fbs",
                   "restecg", "thalach", "exang", "oldpeak", "slope", "ca", "thal"]

    try:
        values = []
        for field in field_names:
            val = request.form.get(field)
            if val is None or val.strip() == "":
                return jsonify({"error": f"Field '{field}' is required."}), 400
            values.append(float(val))

        label, probability, risk_level = mdl.predict(values)

        return jsonify({
            "label":       label,
            "probability": probability,
            "risk_level":  risk_level,
        })

    except ValueError as e:
        return jsonify({"error": f"Invalid input: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


# ─────────────────────────────────────────────
# CHART DATA API
# ─────────────────────────────────────────────

@app.route("/api/chart_data")
@auth.login_required
def chart_data():
    return jsonify(mdl.get_training_history())


# ─────────────────────────────────────────────
# UPLOAD DATASET
# ─────────────────────────────────────────────

@app.route("/upload_dataset", methods=["POST"])
@auth.login_required
def upload_dataset():
    file = request.files.get("dataset_file")
    if not file or file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("dashboard"))

    if not file.filename.endswith(".csv"):
        flash("Only CSV files are accepted.", "error")
        return redirect(url_for("dashboard"))

    save_dir  = os.path.join(_BASE_DIR, "dataset")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "heart.csv")
    file.save(save_path)
    flash("✓ Dataset uploaded successfully! You can now train the model.", "success")
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────

if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
    )
