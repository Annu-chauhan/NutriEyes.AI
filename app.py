import os
import hashlib

from flask import (
    Flask,
    render_template,
    request
)

from werkzeug.utils import secure_filename

from flask_sqlalchemy import SQLAlchemy

from utils.predict import (
    predict_disease,
    validate_retina_image
)

from utils.pdf_report import (
    generate_pdf_report
)
from flask_sqlalchemy import SQLAlchemy

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
# DATABASE MODEL
# =========================

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
# HOME PAGE
# =========================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )

# =========================
# LIVE CAMERA ROUTE
# =========================

@app.route("/camera")
def camera():

    return """

    <h2 style='text-align:center;margin-top:100px;'>

    Live camera is available only in desktop version.

    <br><br>

    Please upload a retinal image.

    <br><br>

    <a href='/'>Back</a>

    </h2>

    """
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
    # CAMERA RISK MODE
    # =========================

    risk_level = "Camera Screening Mode"

    # =========================
    # HASH
    # =========================

    hash_input = f"""

    CameraUser
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

        patient_name="Camera User",

        age=0,

        diabetes="Unknown",

        blood_pressure="Unknown",

        smoking="Unknown",

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
        "camera_report.pdf"
    )

    generate_pdf_report(

        "Camera User",

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

        gradcam_image=(

            "/" + gradcam_image

            if gradcam_image

            else None
        ),

        hash_value=hash_value
    )

# =========================
# REPORT HISTORY PAGE
# =========================

@app.route("/reports")
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

        gradcam_image=(

            "/" + gradcam_image

            if gradcam_image

            else None
        ),

        hash_value=hash_value
    )

# =========================
# MAIN
# =========================

if __name__ == "__main__":

    with app.app_context():

        db.create_all()

    app.run(
        debug=True,
        port=8000
    )