import os
import hashlib
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from flask_sqlalchemy import SQLAlchemy

from utils.predict import (
    predict_disease,
    validate_retina_image
)

from utils.pdf_report import (
    generate_pdf_report
)


# =========================
# LIVE CAMERA IMPORT
# =========================

from utils.camera import (
    capture_eye_image
)

# =========================
# FLASK APP
# =========================

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "nutrieye_clinical_secret_key_2026")

# =========================
# UPLOAD CONFIG
# =========================

UPLOAD_FOLDER = os.path.join(
    "static",
    "uploads"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# =========================
# DATABASE CONFIG
# =========================

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///retina.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================
# DATABASE MODELS
# =========================

class User(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(256),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        default="clinician"
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

# =========================
# AUTHENTICATION DECORATOR & CONTEXT
# =========================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_user():
    if "user_id" in session:
        user = db.session.get(User, session["user_id"])
        return dict(current_user=user)
    return dict(current_user=None)


class Report(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    patient_name = db.Column(
        db.String(100)
    )

    age = db.Column(
        db.Integer
    )

    diabetes = db.Column(
        db.String(20)
    )

    blood_pressure = db.Column(
        db.String(20)
    )

    smoking = db.Column(
        db.String(20)
    )

    disease = db.Column(
        db.String(100)
    )

    confidence = db.Column(
        db.Float
    )

    hash_value = db.Column(
        db.String(256)
    )

    timestamp = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

# CREATE TABLES AFTER MODEL IS DEFINED
with app.app_context():
    db.create_all()
# =========================
# HASH FUNCTION
# =========================

def generate_hash(data):

    return hashlib.sha256(
        data.encode()
    ).hexdigest()

# =========================
# REGISTRATION ROUTE
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("home"))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")
            
        # Check if username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("Username or email already registered.", "danger")
            return render_template("register.html")
            
        # Create user
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))
        
    return render_template("register.html")

# =========================
# LOGIN ROUTE
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))
        
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("login.html")
            
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            flash(f"Welcome back, Dr. {user.username}!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password.", "danger")
            return render_template("login.html")
            
    return render_template("login.html")

# =========================
# LOGOUT ROUTE
# =========================

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("You have logged out successfully.", "success")
    return redirect(url_for("login"))

# =========================
# HOME PAGE
# =========================

@app.route("/")
@login_required
def home():

    return render_template(
        "index.html"
    )

# =========================
# LIVE CAMERA ROUTE
# =========================

@app.route("/camera")
@login_required
def camera():

    return render_template(
        "camera.html"
    )

# =========================
# REPORT HISTORY PAGE
# =========================

@app.route("/reports")
@login_required
def reports():

    all_reports = Report.query.order_by(
        Report.timestamp.desc()
    ).all()

    return render_template(
        "reports.html",
        reports=all_reports
    )

# =========================
# PREDICTION ROUTE
# =========================

@app.route(
    "/predict",
    methods=["POST"]
)
@login_required
def predict():

    # =========================
    # PATIENT DETAILS
    # =========================

    patient_name = request.form.get(
        "patient_name",
        "Unknown"
    )

    age = int(
        request.form.get(
            "age",
            0
        )
    )

    diabetes = request.form.get(
        "diabetes",
        "No"
    )

    blood_pressure = request.form.get(
        "blood_pressure",
        "Normal"
    )

    smoking = request.form.get(
        "smoking",
        "No"
    )

    # =========================
    # RISK ANALYSIS
    # =========================

    risk_level = "Low Risk"

    if (

        age > 50

        or diabetes == "Yes"

        or blood_pressure == "High"

        or smoking == "Yes"

    ):

        risk_level = "High Risk Patient"

    # =========================
    # IMAGE FILE
    # =========================

    file = request.files["image"]

    if file.filename == "":

        return "No file selected"

    # =========================
    # SAVE IMAGE
    # =========================

    filename = secure_filename(
        file.filename
    )

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(filepath)

    # =========================
    # VALIDATE IMAGE
    # =========================

    valid, message = validate_retina_image(
        filepath
    )

    if not valid:

        return message

    # =========================
    # AI PREDICTION
    # =========================

    result = predict_disease(
        filepath
    )

    prediction = result["disease"]

    confidence = result["confidence"]

    recommendation = result["recommendation"]

    top2_predictions = result["top2_predictions"]

    gradcam_image = result.get(
        "gradcam_image"
    )

    # =========================
    # HASH GENERATION
    # =========================

    hash_input = f"""

    {patient_name}
    {prediction}
    {confidence}

    """

    hash_value = generate_hash(
        hash_input
    )

    # =========================
    # SAVE REPORT
    # =========================

    report = Report(

        patient_name=patient_name,

        age=age,

        diabetes=diabetes,

        blood_pressure=blood_pressure,

        smoking=smoking,

        disease=prediction,

        confidence=confidence,

        hash_value=hash_value
    )

    db.session.add(report)

    db.session.commit()

    # =========================
    # PDF REPORT
    # =========================

    pdf_path = os.path.join(
        "static",
        "report.pdf"
    )

    generate_pdf_report(

        patient_name,

        prediction,

        confidence,

        recommendation,

        hash_value,

        pdf_path
    )

    # =========================
    # RESULT PAGE
    # =========================

    return render_template(

        "result.html",

        uploaded_image="/" + filepath.replace("\\", "/"),

        prediction=prediction,

        confidence=confidence,

        recommendation=recommendation,

        top2_predictions=top2_predictions,

        risk_level=risk_level,

        pdf_report="/" + pdf_path.replace("\\", "/"),

        gradcam_image=gradcam_image,

        hash_value=hash_value
    )

# =========================
# MAIN
# =========================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=8000
    )