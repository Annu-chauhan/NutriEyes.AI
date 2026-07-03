import os
import hashlib
import datetime
import secrets
import logging
import jwt
from functools import wraps
from flasgger import Swagger


from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    g
)

from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

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

if "SPACE_ID" in os.environ:
    app.config.update(
        SESSION_COOKIE_SAMESITE="None",
        SESSION_COOKIE_SECURE=True
    )
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Initialize CORS
CORS(app, supports_credentials=True)

# Initialize Swagger API Documentation
swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "NutriEye AI Diagnostics & Security API",
        "description": "Interactive API Documentation for the NutriEye clinician authentication portal, disease screening models, and patient report systems.",
        "version": "2.5.0",
        "contact": {
            "name": "Clinical AI Support",
            "email": "support@nutrieye.ai"
        }
    },
    "securityDefinitions": {
        "AccessCookie": {
            "type": "apiKey",
            "name": "access_token",
            "in": "cookie",
            "description": "JWT Access Token stored in HttpOnly cookies."
        },
        "RefreshCookie": {
            "type": "apiKey",
            "name": "refresh_token",
            "in": "cookie",
            "description": "JWT Refresh Token stored in HttpOnly cookies."
        }
    }
})

# Initialize Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Initialize Argon2 Password Hasher
ph = PasswordHasher()

# Setup Audit Logger
os.makedirs("logs", exist_ok=True)
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)
# Clear handlers to avoid duplicate logs on hot reload
if audit_logger.hasHandlers():
    audit_logger.handlers.clear()
audit_handler = logging.FileHandler("logs/audit.log")
audit_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
audit_logger.addHandler(audit_handler)

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
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="doctor") # doctor, admin, patient, researcher
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    token_version = db.Column(db.Integer, default=1)
    failed_login_attempts = db.Column(db.Integer, default=0)
    lockout_until = db.Column(db.DateTime, nullable=True)
    mfa_otp = db.Column(db.String(6), nullable=True)
    mfa_otp_expiry = db.Column(db.DateTime, nullable=True)
    mfa_otp_attempts = db.Column(db.Integer, default=0)
    totp_secret = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), default="Other") # Male, Female, Other
    diabetes = db.Column(db.String(20), default="No")
    blood_pressure = db.Column(db.String(20), default="Normal")
    smoking = db.Column(db.String(20), default="No")
    doctor_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    reports = db.relationship('Report', backref='patient', lazy=True, cascade="all, delete-orphan")

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True)
    patient_name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    diabetes = db.Column(db.String(20))
    blood_pressure = db.Column(db.String(20))
    smoking = db.Column(db.String(20))
    disease = db.Column(db.String(100))
    confidence = db.Column(db.Float)
    severity_stage = db.Column(db.String(50), nullable=True)
    hash_value = db.Column(db.String(256))
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# CREATE TABLES AFTER MODEL IS DEFINED (WITH AUTO RE-CREATION SCHEMA VERIFICATION)
with app.app_context():
    try:
        # Run a query to verify user (totp_secret), patient, and report (severity_stage) tables are present
        db.session.execute(db.text("SELECT totp_secret FROM user LIMIT 1")).all()
        db.session.execute(db.text("SELECT doctor_notes FROM patient LIMIT 1")).all()
        db.session.execute(db.text("SELECT severity_stage FROM report LIMIT 1")).all()
    except Exception:
        db.session.rollback()
        print("Database schema mismatch detected (missing MFA, patient, or severity_stage columns). Recreating database tables...")
        db.drop_all()
    db.create_all()


# =========================
# JWT & SECURITY HELPER FUNCTIONS
# =========================

def set_jwt_cookies(response, access_token, refresh_token):
    samesite = "None" if "SPACE_ID" in os.environ else "Lax"
    secure = True
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=15*60
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=7*24*60*60
    )

def clear_jwt_cookies(response):
    samesite = "None" if "SPACE_ID" in os.environ else "Lax"
    response.delete_cookie("access_token", samesite=samesite)
    response.delete_cookie("refresh_token", samesite=samesite)

# =========================
# MIDDLEWARE AND DECORATORS
# =========================

@app.before_request
def load_user_from_jwt():
    g.user = None
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")
    
    if access_token:
        try:
            payload = jwt.decode(access_token, app.secret_key, algorithms=["HS256"])
            user = db.session.get(User, payload["user_id"])
            if user and user.token_version == payload.get("token_version"):
                g.user = user
                return
        except jwt.ExpiredSignatureError:
            pass
        except jwt.PyJWTError:
            pass
            
    if refresh_token:
        try:
            payload = jwt.decode(refresh_token, app.secret_key, algorithms=["HS256"])
            user = db.session.get(User, payload["user_id"])
            if user and user.token_version == payload.get("token_version"):
                new_access_payload = {
                    "user_id": user.id,
                    "role": user.role,
                    "token_version": user.token_version,
                    "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
                }
                new_access_token = jwt.encode(new_access_payload, app.secret_key, algorithm="HS256")
                g.user = user
                g.new_access_token = new_access_token
        except jwt.PyJWTError:
            pass

@app.after_request
def set_secure_headers_and_cookies(response):
    # Enforce Secure Headers
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://omnidim.io; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:;"
    
    if hasattr(g, "new_access_token") and g.new_access_token:
        samesite = "None" if "SPACE_ID" in os.environ else "Lax"
        secure = True
        response.set_cookie(
            "access_token",
            g.new_access_token,
            httponly=True,
            secure=secure,
            samesite=samesite,
            max_age=15*60
        )
    return response

# CSRF PROTECTION Form Check Helper
@app.before_request
def verify_csrf_token():
    if request.method == "POST":
        if request.path in ["/predict", "/login", "/register", "/forgot-password", "/verify-otp", "/setup-mfa"] or request.path.startswith("/reset-password"):
            token_in_form = request.form.get("csrf_token")
            token_in_session = session.get("csrf_token")
            if not token_in_session or token_in_form != token_in_session:
                audit_logger.warning(f"CSRF violation detected on path {request.path} - IP: {request.remote_addr}")
                flash("Security verification failed. Please try again.", "danger")
                return redirect(url_for("home"))

@app.context_processor
def inject_security_tokens():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return dict(
        current_user=g.user if hasattr(g, "user") else None,
        csrf_token=session["csrf_token"]
    )

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def roles_accepted(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.user:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("login"))
            if g.user.role not in roles:
                audit_logger.warning(f"Unauthorized RBAC access attempt by User {g.user.username} (ID: {g.user.id}, Role: {g.user.role}) on route {request.path}")
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("home"))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

# =========================
# HASH FUNCTION
# =========================

def generate_hash(data):
    return hashlib.sha256(data.encode()).hexdigest()

# =========================
# SMTP EMAIL NOTIFICATION HELPERS
# =========================

def send_verification_email(to_email, verification_link):
    mail_server = os.environ.get("MAIL_SERVER")
    mail_port = os.environ.get("MAIL_PORT")
    mail_username = os.environ.get("MAIL_USERNAME")
    mail_password = os.environ.get("MAIL_PASSWORD")
    mail_sender = os.environ.get("MAIL_SENDER", "noreply@nutrieye.ai")
    
    if mail_server and mail_port and mail_username and mail_password:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        try:
            msg = MIMEMultipart()
            msg["From"] = mail_sender
            msg["To"] = to_email
            msg["Subject"] = "NutriEye - Verify Your Email"
            
            body = f"Hello,\n\nPlease verify your email to activate your account:\n{verification_link}\n\nBest,\nNutriEye Team"
            msg.attach(MIMEText(body, "plain"))
            
            port = int(mail_port)
            if port == 465:
                server = smtplib.SMTP_SSL(mail_server, port)
            else:
                server = smtplib.SMTP(mail_server, port)
                server.starttls()
                
            server.login(mail_username, mail_password)
            server.sendmail(mail_sender, to_email, msg.as_string())
            server.quit()
            return True, "Email sent"
        except Exception as e:
            return False, str(e)
    return False, "SMTP not configured"

def send_reset_email(to_email, reset_link):
    mail_server = os.environ.get("MAIL_SERVER")
    mail_port = os.environ.get("MAIL_PORT")
    mail_username = os.environ.get("MAIL_USERNAME")
    mail_password = os.environ.get("MAIL_PASSWORD")
    mail_sender = os.environ.get("MAIL_SENDER", "noreply@nutrieye.ai")
    
    if mail_server and mail_port and mail_username and mail_password:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        try:
            msg = MIMEMultipart()
            msg["From"] = mail_sender
            msg["To"] = to_email
            msg["Subject"] = "NutriEye - Password Reset Request"
            
            body = f"Hello,\n\nPlease reset your password using the link below:\n{reset_link}\n\nThis link will expire in 1 hour.\n\nBest,\nNutriEye Team"
            msg.attach(MIMEText(body, "plain"))
            
            port = int(mail_port)
            if port == 465:
                server = smtplib.SMTP_SSL(mail_server, port)
            else:
                server = smtplib.SMTP(mail_server, port)
                server.starttls()
                
            server.login(mail_username, mail_password)
            server.sendmail(mail_sender, to_email, msg.as_string())
            server.quit()
            return True, "Email sent"
        except Exception as e:
            return False, str(e)
    return False, "SMTP not configured"

def send_otp_email(to_email, otp_code):
    mail_server = os.environ.get("MAIL_SERVER")
    mail_port = os.environ.get("MAIL_PORT")
    mail_username = os.environ.get("MAIL_USERNAME")
    mail_password = os.environ.get("MAIL_PASSWORD")
    mail_sender = os.environ.get("MAIL_SENDER", "noreply@nutrieye.ai")
    
    if mail_server and mail_port and mail_username and mail_password:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        try:
            msg = MIMEMultipart()
            msg["From"] = mail_sender
            msg["To"] = to_email
            msg["Subject"] = "NutriEye - Your One-Time verification Code (OTP)"
            
            body = f"Hello,\n\nYour One-Time verification Code (OTP) to log in to NutriEye is:\n\n{otp_code}\n\nThis code will expire in 5 minutes. Do not share it with anyone.\n\nBest,\nNutriEye Team"
            msg.attach(MIMEText(body, "plain"))
            
            port = int(mail_port)
            if port == 465:
                server = smtplib.SMTP_SSL(mail_server, port)
            else:
                server = smtplib.SMTP(mail_server, port)
                server.starttls()
                
            server.login(mail_username, mail_password)
            server.sendmail(mail_sender, to_email, msg.as_string())
            server.quit()
            return True, "Email sent"
        except Exception as e:
            return False, str(e)
    return False, "SMTP not configured"


# =========================
# REGISTRATION ROUTE
# =========================

@app.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def register():
    """
    Register a new clinician account
    ---
    tags:
      - Authentication
    parameters:
      - name: username
        in: formData
        type: string
        required: true
        description: Clinician full name (e.g. Dr. Watson)
      - name: email
        in: formData
        type: string
        required: true
        description: Unique email address
      - name: password
        in: formData
        type: string
        required: true
        description: Account password (minimum 8 characters)
      - name: role
        in: formData
        type: string
        required: true
        enum: [doctor, admin, patient, researcher]
        description: Access role for RBAC control
    responses:
      200:
        description: Renders the registration HTML form (GET).
      302:
        description: Redirects to /login on successful registration.
      400:
        description: Validation mismatch or missing fields.
      429:
        description: Rate limit exceeded (max 5 requests per minute).
    """
    if g.user:
        return redirect(url_for("home"))
        
    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "doctor").strip()
        
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")
            
        import re
        if (len(password) < 8 or
            not re.search(r"[a-z]", password) or
            not re.search(r"[A-Z]", password) or
            not re.search(r"\d", password) or
            not re.search(r"[^a-zA-Z0-9]", password)):
            flash("Password does not meet complexity requirements. It must contain at least 8 characters, including uppercase, lowercase, number, and special character.", "danger")
            return render_template("register.html")
            
        # Check if username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("Username or email already registered.", "danger")
            return render_template("register.html")
            
        # Create user with Argon2 and verification token
        hashed_password = ph.hash(password)
        v_token = secrets.token_urlsafe(32)
        
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            role=role,
            is_verified=False,
            verification_token=v_token
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        verification_link = url_for("verify_email", token=v_token, _external=True)
        is_sent, mail_msg = send_verification_email(email, verification_link)
        
        audit_logger.info(f"User registered: {username} (ID: {new_user.id}) - Role: {role} - Verified: False - IP: {request.remote_addr}")
        
        if is_sent:
            flash("Registration successful! A verification email has been sent.", "success")
        else:
            flash(f"Registration successful! [Demo Mode] Email verification link: {verification_link}", "info")
            
        return redirect(url_for("login"))
        
    return render_template("register.html")

# =========================
# VERIFY EMAIL ROUTE
# =========================

@app.route("/verify-email/<token>")
@limiter.limit("5 per minute")
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if user:
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        audit_logger.info(f"User email verified: {user.username} (ID: {user.id}) - IP: {request.remote_addr}")
        flash("Email verified successfully! You can now log in.", "success")
    else:
        flash("Invalid or expired verification link.", "danger")
    return redirect(url_for("login"))

# =========================
# LOGIN ROUTE
# =========================

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    """
    Clinician authentication portal
    ---
    tags:
      - Authentication
    parameters:
      - name: email
        in: formData
        type: string
        required: true
        description: Clinician registered email
      - name: password
        in: formData
        type: string
        required: true
        description: Account password
    responses:
      200:
        description: Renders login HTML form or returns error (e.g. locked account).
      302:
        description: Sets JWT cookies and redirects to dashboard on success.
      401:
        description: Invalid credentials or account lockout trigger.
      429:
        description: Rate limit exceeded.
    """
    if g.user:
        return redirect(url_for("home"))
        
    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("login.html")
            
        user = User.query.filter_by(email=email).first()
        if user:
            # Check lockout
            if user.lockout_until and user.lockout_until > datetime.datetime.utcnow():
                lockout_left = int((user.lockout_until - datetime.datetime.utcnow()).total_seconds())
                flash(f"Account locked. Try again in {lockout_left} seconds.", "danger")
                return render_template("login.html")
                
            # Check verification
            if not user.is_verified:
                v_link = url_for("verify_email", token=user.verification_token, _external=True)
                flash(f"Verify your email before logging in. [Demo Mode] Activation Link: {v_link}", "warning")
                return render_template("login.html")
                
            try:
                ph.verify(user.password_hash, password)
                # Success
                user.failed_login_attempts = 0
                user.lockout_until = None
                db.session.commit()
                
                # Save user ID pending verification in session
                session["mfa_pending_user_id"] = user.id
                
                if not user.totp_secret:
                    # Redirect to first-time setup
                    audit_logger.info(f"MFA Setup Triggered: Authenticator setup required for {user.username} (ID: {user.id}) - IP: {request.remote_addr}")
                    return redirect(url_for("setup_mfa"))
                else:
                    # Redirect to verify OTP
                    audit_logger.info(f"MFA Challenge Triggered: Authenticator verification required for {user.username} (ID: {user.id}) - IP: {request.remote_addr}")
                    return redirect(url_for("verify_otp"))
                
            except VerifyMismatchError:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.lockout_until = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
                    audit_logger.warning(f"Account locked: {user.username} (ID: {user.id}) after 5 failed login attempts - IP: {request.remote_addr}")
                    flash("Account locked for 15 minutes due to 5 failed attempts.", "danger")
                else:
                    flash(f"Invalid email or password. Attempts remaining: {5 - user.failed_login_attempts}", "danger")
                db.session.commit()
                return render_template("login.html")
        else:
            flash("Invalid email or password.", "danger")
            return render_template("login.html")
            
    return render_template("login.html")

# =========================
# SETUP MFA (TOTP) ROUTE
# =========================

@app.route("/setup-mfa", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def setup_mfa():
    """
    Setup Multi-Factor Authentication (TOTP pairing)
    """
    pending_user_id = session.get("mfa_pending_user_id")
    if not pending_user_id:
        flash("No active login session. Please log in first.", "danger")
        return redirect(url_for("login"))
        
    user = db.session.get(User, pending_user_id)
    if not user:
        session.pop("mfa_pending_user_id", None)
        flash("Invalid session. Please login again.", "danger")
        return redirect(url_for("login"))
        
    if user.totp_secret:
        # Already setup, redirect to verify
        return redirect(url_for("verify_otp"))
        
    import pyotp
    import urllib.parse
    
    if request.method == "POST":
        otp_code = request.form.get("otp_code", "").strip()
        temp_secret = session.get("temp_totp_secret")
        
        if not temp_secret:
            flash("Session expired. Please reload the page to pair again.", "danger")
            return redirect(url_for("setup_mfa"))
            
        totp = pyotp.TOTP(temp_secret)
        if totp.verify(otp_code, valid_window=1):
            # Success! Pair device
            user.totp_secret = temp_secret
            user.mfa_otp_attempts = 0
            db.session.commit()
            
            session.pop("temp_totp_secret", None)
            session.pop("mfa_pending_user_id", None)
            
            # Emit JWT cookies and log in user
            access_payload = {
                "user_id": user.id,
                "role": user.role,
                "token_version": user.token_version,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
            }
            access_token = jwt.encode(access_payload, app.secret_key, algorithm="HS256")
            
            refresh_payload = {
                "user_id": user.id,
                "token_version": user.token_version,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
            }
            refresh_token = jwt.encode(refresh_payload, app.secret_key, algorithm="HS256")
            
            audit_logger.info(f"Doctor MFA Paired successfully: {user.username} (ID: {user.id}) - IP: {request.remote_addr}")
            
            response = redirect(url_for("home"))
            set_jwt_cookies(response, access_token, refresh_token)
            flash(f"MFA configured successfully! Welcome back, Dr. {user.username}!", "success")
            return response
        else:
            flash("Incorrect verification code. Please scan the QR code and enter the current 6-digit code shown in your app.", "danger")
            return redirect(url_for("setup_mfa"))
            
    # GET: generate secret and provisioning URI
    temp_secret = session.get("temp_totp_secret")
    if not temp_secret:
        temp_secret = pyotp.random_base32()
        session["temp_totp_secret"] = temp_secret
        
    totp = pyotp.TOTP(temp_secret)
    provisioning_url = totp.provisioning_uri(name=user.email, issuer_name="NutriEye")
    
    # We use qrserver API to render the QR code securely
    qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(provisioning_url)}"
    
    return render_template("setup_mfa.html", qr_code_url=qr_code_url, secret=temp_secret)


# =========================
# VERIFY OTP ROUTE
# =========================

@app.route("/verify-otp", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def verify_otp():
    """
    Verify Multi-Factor Authentication Code
    ---
    tags:
      - Authentication
    parameters:
      - name: otp_code
        in: formData
        type: string
        required: true
        description: 6-digit verification code from Google Authenticator
    responses:
      200:
        description: Renders the OTP verification HTML page.
      302:
        description: Redirects to dashboard upon successful verification.
      400:
        description: Invalid code or maximum attempts reached.
      401:
        description: No verification process is active for this session.
    """
    # Verify there is a pending user session
    pending_user_id = session.get("mfa_pending_user_id")
    if not pending_user_id:
        flash("No login attempt is currently active. Please log in first.", "danger")
        return redirect(url_for("login"))
        
    user = db.session.get(User, pending_user_id)
    if not user:
        session.pop("mfa_pending_user_id", None)
        flash("Invalid session. Please login again.", "danger")
        return redirect(url_for("login"))
        
    if not user.totp_secret:
        # MFA has not been paired, redirect to setup
        return redirect(url_for("setup_mfa"))
        
    if request.method == "POST":
        otp_code = request.form.get("otp_code", "").strip()
        
        # Check attempts
        if user.mfa_otp_attempts >= 3:
            # Clear pending verify session
            user.mfa_otp_attempts = 0
            db.session.commit()
            session.pop("mfa_pending_user_id", None)
            
            audit_logger.warning(f"MFA Locked: Locked verification session for {user.username} (ID: {user.id}) due to exceeding wrong attempts - IP: {request.remote_addr}")
            flash("Verification failed: Exceeded maximum attempts. Please log in again.", "danger")
            return redirect(url_for("login"))
            
        import pyotp
        totp = pyotp.TOTP(user.totp_secret)
        
        # Check correct code
        if totp.verify(otp_code, valid_window=1):
            # Success! Reset attempts counter
            user.mfa_otp_attempts = 0
            db.session.commit()
            session.pop("mfa_pending_user_id", None)
            
            # Emit JWT cookies and log in user
            access_payload = {
                "user_id": user.id,
                "role": user.role,
                "token_version": user.token_version,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
            }
            access_token = jwt.encode(access_payload, app.secret_key, algorithm="HS256")
            
            refresh_payload = {
                "user_id": user.id,
                "token_version": user.token_version,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
            }
            refresh_token = jwt.encode(refresh_payload, app.secret_key, algorithm="HS256")
            
            audit_logger.info(f"Doctor Login (MFA Successful): {user.username} (ID: {user.id}) - IP: {request.remote_addr}")
            
            response = redirect(url_for("home"))
            set_jwt_cookies(response, access_token, refresh_token)
            flash(f"Welcome back, Dr. {user.username}!", "success")
            return response
        else:
            user.mfa_otp_attempts += 1
            db.session.commit()
            
            remaining = 3 - user.mfa_otp_attempts
            audit_logger.warning(f"MFA Attempt Failure: Incorrect OTP code for {user.username} (ID: {user.id}) - Remaining attempts: {remaining} - IP: {request.remote_addr}")
            
            if remaining <= 0:
                # Force redirect out
                user.mfa_otp_attempts = 0
                db.session.commit()
                session.pop("mfa_pending_user_id", None)
                flash("Exceeded maximum verification attempts. Please log in again.", "danger")
                return redirect(url_for("login"))
                
            flash(f"Incorrect verification code. Attempts remaining: {remaining}", "danger")
            return redirect(url_for("verify_otp"))
            
    return render_template("verify_otp.html")

# =========================
# FORGOT PASSWORD ROUTE
# =========================

@app.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def forgot_password():
    """
    Initiate clinician password recovery
    ---
    tags:
      - Authentication
    parameters:
      - name: email
        in: formData
        type: string
        required: true
        description: Registered clinician email address
    responses:
      200:
        description: Sends link (Production Mode) or flashes link on screen (Demo Mode).
      429:
        description: Rate limit exceeded.
    """
    if request.method == "POST":

        email = request.form.get("email", "").strip()
        if not email:
            flash("Email is required.", "danger")
            return render_template("forgot_password.html")
            
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            db.session.commit()
            
            reset_link = url_for("reset_password", token=token, _external=True)
            is_sent, mail_msg = send_reset_email(email, reset_link)
            
            audit_logger.info(f"Password reset link requested for: {email} - IP: {request.remote_addr}")
            
            if is_sent:
                flash("A password reset link has been sent to your email.", "success")
            else:
                flash(f"Password reset link generated: [Demo Mode] {reset_link}", "info")
        else:
            flash("If that email address exists in our database, a reset link has been sent.", "info")
            
    return render_template("forgot_password.html")

# =========================
# RESET PASSWORD ROUTE
# =========================

@app.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or (user.reset_token_expiry and user.reset_token_expiry < datetime.datetime.utcnow()):
        flash("Invalid or expired reset link.", "danger")
        return redirect(url_for("login"))
        
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template("reset_password.html", token=token)
            
        import re
        if (len(password) < 8 or
            not re.search(r"[a-z]", password) or
            not re.search(r"[A-Z]", password) or
            not re.search(r"\d", password) or
            not re.search(r"[^a-zA-Z0-9]", password)):
            flash("Password does not meet complexity requirements. It must contain at least 8 characters, including uppercase, lowercase, number, and special character.", "danger")
            return render_template("reset_password.html", token=token)
            
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", token=token)
            
        user.password_hash = ph.hash(password)
        user.reset_token = None
        user.reset_token_expiry = None
        user.token_version += 1 # Invalidate active device sessions
        db.session.commit()
        
        audit_logger.info(f"Password Changed: {user.username} (ID: {user.id}) successfully updated password - IP: {request.remote_addr}")
        flash("Password successfully reset! Please log in.", "success")
        return redirect(url_for("login"))
        
    return render_template("reset_password.html", token=token)

# =========================
# LOGOUT ROUTE
# =========================

@app.route("/logout")
def logout():
    if g.user:
        audit_logger.info(f"User logged out: {g.user.username} (ID: {g.user.id}) - IP: {request.remote_addr}")
    response = redirect(url_for("login"))
    clear_jwt_cookies(response)
    flash("You have logged out successfully.", "success")
    return response

# =========================
# LOGOUT ALL DEVICES ROUTE
# =========================

@app.route("/logout-all")
@login_required
def logout_all():
    user = g.user
    user.token_version += 1
    db.session.commit()
    
    audit_logger.info(f"User logged out from all devices: {user.username} (ID: {user.id}) - IP: {request.remote_addr}")
    
    response = redirect(url_for("login"))
    clear_jwt_cookies(response)
    flash("Successfully logged out from all active devices.", "success")
    return response

# =========================
# HOME PAGE
# =========================

@app.route("/")
@login_required
@roles_accepted("admin", "doctor", "researcher")
def home():
    patient_id = request.args.get("patient_id")
    patient = None
    if patient_id:
        patient = db.session.get(Patient, int(patient_id))
    return render_template("index.html", patient=patient)


# =========================
# LIVE CAMERA ROUTE
# =========================

@app.route("/camera")
@login_required
@roles_accepted("admin", "doctor", "researcher")
def camera():
    return render_template("camera.html")

# =========================
# REPORT HISTORY PAGE
# =========================

@app.route("/reports")
@login_required
@roles_accepted("admin", "doctor", "researcher")
def reports():
    all_reports = Report.query.order_by(Report.timestamp.desc()).all()
    audit_logger.info(f"Patient Viewed: Report archives accessed by User {g.user.id} ({g.user.username}) - IP: {request.remote_addr}")
    return render_template("reports.html", reports=all_reports)

# =========================
# PREDICTION ROUTE
# =========================

@app.route("/predict", methods=["POST"])
@login_required
@roles_accepted("admin", "doctor", "researcher")
@limiter.limit("10 per minute")
def predict():
    """
    Analyze retinal fundus scan using AI
    ---
    tags:
      - AI Diagnosis
    security:
      - AccessCookie: []
      - RefreshCookie: []
    parameters:
      - name: patient_name
        in: formData
        type: string
        required: true
        description: Patient Name
      - name: age
        in: formData
        type: integer
        required: true
        description: Patient Age
      - name: diabetes
        in: formData
        type: string
        enum: [Yes, No]
        required: true
        description: Diabetic status
      - name: blood_pressure
        in: formData
        type: string
        enum: [Normal, High]
        required: true
        description: Hypertension status
      - name: smoking
        in: formData
        type: string
        enum: [Yes, No]
        required: true
        description: Smoking status
      - name: image
        in: formData
        type: file
        required: true
        description: Retinal fundus image scan (.jpg, .jpeg, .png, max 5MB)
    responses:
      200:
        description: Returns result page displaying diagnostic result, confidence score, and Grad-CAM heatmap.
      302:
        description: Redirects to home page on validation errors.
      403:
        description: Forbidden (insufficient RBAC permissions).
      429:
        description: Rate limit exceeded (max 10 requests per minute).
    """
    patient_name = request.form.get("patient_name", "Unknown").strip()

    age_str = request.form.get("age", "0").strip()
    diabetes = request.form.get("diabetes", "No").strip()
    blood_pressure = request.form.get("blood_pressure", "Normal").strip()
    smoking = request.form.get("smoking", "No").strip()
    
    # Input validation
    try:
        age = int(age_str)
        if age < 0 or age > 120:
            flash("Invalid patient age.", "danger")
            return redirect(url_for("home"))
    except ValueError:
        flash("Patient age must be an integer.", "danger")
        return redirect(url_for("home"))
        
    if not patient_name:
        flash("Patient name is required.", "danger")
        return redirect(url_for("home"))
        
    risk_level = "Low Risk"
    if age > 50 or diabetes == "Yes" or blood_pressure == "High" or smoking == "Yes":
        risk_level = "High Risk Patient"
        
    file = request.files.get("image")
    if not file or file.filename == "":
        flash("No retinal scan file selected.", "danger")
        return redirect(url_for("home"))
        
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    
    # Validate image security (magic bytes, size, integrity)
    valid, message = validate_retina_image(filepath)
    if not valid:
        if os.path.exists(filepath):
            os.remove(filepath)
        flash(message, "danger")
        return redirect(url_for("home"))
        
    # AI prediction
    result = predict_disease(filepath)
    prediction = result["disease"]
    confidence = result["confidence"]
    recommendation = result["recommendation"]
    top2_predictions = result["top2_predictions"]
    gradcam_image = result.get("gradcam_image")
    
    # Cryptographic Hash of report parameters
    hash_input = f"{patient_name}{prediction}{confidence}"
    hash_value = generate_hash(hash_input)
    
    # Retrieve or auto-register patient
    patient_id_form = request.form.get("patient_id")
    patient = None
    if patient_id_form and patient_id_form != "None":
        try:
            patient = db.session.get(Patient, int(patient_id_form))
        except ValueError:
            pass
            
    if not patient:
        # Check if patient name exists already
        patient = Patient.query.filter_by(name=patient_name).first()
        if not patient:
            # Create a new patient profile automatically
            patient = Patient(
                name=patient_name,
                age=age,
                diabetes=diabetes,
                blood_pressure=blood_pressure,
                smoking=smoking
            )
            db.session.add(patient)
            db.session.commit()
            audit_logger.info(f"Patient Registry: New profile auto-created for patient {patient_name} - IP: {request.remote_addr}")

    # AI Explanation mapping
    explanations = {
        "Glaucoma": "Predicted Glaucoma due to high cup-to-disc ratio (vertical enlargement), presence of neuroretinal rim thinning, and local retinal nerve fiber layer (RNFL) loss.",
        "Diabetic Retinopathy": "Predicted Diabetic Retinopathy due to signs of microaneurysms, retinal hemorrhages, and hard exudates secondary to long-standing hyperglycemia.",
        "Cataract": "Predicted Cataract due to diffuse lens opacity, loss of red reflex, and significant attenuation of optical scan signal.",
        "Normal": "Retinal morphology appears intact. Optic disc cup-to-disc ratio is within physiological limits (~0.3), macula shows normal foveal reflex, and vascular arches are free of exudates or hemorrhages."
    }
    explanation = explanations.get(prediction, "Retinal scans analyzed using convolutional neural network architectures to detect patterns of micro-vascular anomalies, optic disc changes, or focal signal absorption.")
    model_version = "VGG16-RetinaNet v1.2"

    # Determine severity stage
    severity_stage = "Healthy"
    if prediction != "Normal":
        if confidence < 70.0:
            severity_stage = "Early Stage"
        elif confidence < 85.0:
            severity_stage = "Moderate Stage"
        else:
            severity_stage = "Advanced Stage"

    # Cryptographic Hash of report parameters
    hash_input = f"{patient_name}{prediction}{confidence}"
    hash_value = generate_hash(hash_input)
    
    # Save Report record to SQLite linked to Patient
    report = Report(
        patient_id=patient.id,
        patient_name=patient_name,
        age=age,
        diabetes=diabetes,
        blood_pressure=blood_pressure,
        smoking=smoking,
        disease=prediction,
        confidence=confidence,
        severity_stage=severity_stage,
        hash_value=hash_value
    )
    db.session.add(report)
    db.session.commit()
    
    # Dynamic verify URL for QR code
    verify_url = f"{request.scheme}://{request.host}/verify-report/{hash_value}"
    
    # PDF generation
    pdf_path = os.path.join("static", "report.pdf")
    generate_pdf_report(
        patient_name,
        prediction,
        confidence,
        recommendation,
        hash_value,
        pdf_path,
        verify_url=verify_url,
        severity_stage=severity_stage
    )
    
    # Audit log prediction
    audit_logger.info(f"Prediction Created: User {g.user.id} ({g.user.username}) generated screening for patient {patient_name} (ID: {patient.id}) - Result: {prediction} - Severity: {severity_stage} - Confidence: {confidence}% - IP: {request.remote_addr}")
    
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
        hash_value=hash_value,
        explanation=explanation,
        model_version=model_version,
        patient=patient,
        severity_stage=severity_stage
    )


# =========================
# HEALTH CHECK ROUTE
# =========================

@app.route("/health")
@limiter.exempt
def health():
    """
    Service Health Status
    ---
    tags:
      - Monitoring
    responses:
      200:
        description: System is fully functional.
        schema:
          type: object
          properties:
            status:
              type: string
              example: healthy
            database:
              type: string
              example: connected
            timestamp:
              type: string
              example: "2026-07-02T13:00:00Z"
      500:
        description: System database is disconnected or degraded.
    """
    db_ok = False
    try:
        db.session.execute(db.text("SELECT 1")).all()
        db_ok = True
    except Exception as e:
        audit_logger.critical(f"Database health check failed: {str(e)}")
        
    status_code = 200 if db_ok else 500
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }, status_code

# =========================
# PATIENT REGISTRY ROUTES
# =========================

@app.route("/patients", methods=["GET", "POST"])
@login_required
@roles_accepted("admin", "doctor", "researcher")
def patients():
    """
    Patient Registry List & Add
    ---
    tags:
      - Patient Management
    parameters:
      - name: name
        in: formData
        type: string
        required: false
        description: Patient Name (For adding new)
      - name: age
        in: formData
        type: integer
        required: false
        description: Patient Age
      - name: gender
        in: formData
        type: string
        enum: [Male, Female, Other]
        required: false
        description: Patient Gender
      - name: diabetes
        in: formData
        type: string
        enum: [Yes, No]
        required: false
        description: Diabetic status
      - name: blood_pressure
        in: formData
        type: string
        enum: [Normal, High]
        required: false
        description: Hypertension status
      - name: smoking
        in: formData
        type: string
        enum: [Yes, No]
        required: false
        description: Smoking status
    responses:
      200:
        description: Renders the patients list HTML page.
    """
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age_str = request.form.get("age", "").strip()
        gender = request.form.get("gender", "Other").strip()
        diabetes = request.form.get("diabetes", "No").strip()
        blood_pressure = request.form.get("blood_pressure", "Normal").strip()
        smoking = request.form.get("smoking", "No").strip()
        
        if not name or not age_str:
            flash("Patient name and age are required.", "danger")
            return redirect(url_for("patients"))
            
        try:
            age = int(age_str)
        except ValueError:
            flash("Patient age must be an integer.", "danger")
            return redirect(url_for("patients"))
            
        new_patient = Patient(
            name=name,
            age=age,
            gender=gender,
            diabetes=diabetes,
            blood_pressure=blood_pressure,
            smoking=smoking
        )
        db.session.add(new_patient)
        db.session.commit()
        
        audit_logger.info(f"Patient Registry: Registered Patient {new_patient.name} (ID: {new_patient.id}) by User {g.user.id} ({g.user.username}) - IP: {request.remote_addr}")
        flash(f"Patient {name} has been successfully registered.", "success")
        return redirect(url_for("patients"))
        
    search_query = request.args.get("search", "").strip()
    if search_query:
        patient_list = Patient.query.filter(Patient.name.ilike(f"%{search_query}%")).all()
    else:
        patient_list = Patient.query.order_by(Patient.name.asc()).all()
        
    return render_template("patients.html", patients=patient_list, search_query=search_query)


@app.route("/patients/<int:id>", methods=["GET", "POST"])
@login_required
@roles_accepted("admin", "doctor", "researcher")
def patient_detail(id):
    """
    Patient Profile History & Timeline
    ---
    tags:
      - Patient Management
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: Patient Database ID
      - name: doctor_notes
        in: formData
        type: string
        required: false
        description: Text notes to add/update for patient
    responses:
      200:
        description: Renders the patient timeline & profile details.
    """
    patient = db.session.get(Patient, id)
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("patients"))
        
    if request.method == "POST":
        notes = request.form.get("doctor_notes", "")
        patient.doctor_notes = notes
        db.session.commit()
        audit_logger.info(f"Patient Registry: Notes updated for Patient {patient.name} (ID: {patient.id}) by User {g.user.id} - IP: {request.remote_addr}")
        flash("Clinical notes updated successfully.", "success")
        return redirect(url_for("patient_detail", id=id))
        
    return render_template("patient_detail.html", patient=patient)


# =========================
# QR REPORT VERIFICATION
# =========================

@app.route("/verify-report/<hash_value>")
@limiter.exempt  # Public auditor access
def verify_report(hash_value):
    """
    Cryptographic Report QR Verification
    ---
    tags:
      - Security
    parameters:
      - name: hash_value
        in: path
        type: string
        required: true
        description: Cryptographic sha256 hash of report parameters
    responses:
      200:
        description: Verifies authenticity of the clinical report.
      404:
        description: Verification failed. Report hash not found.
    """
    report = Report.query.filter_by(hash_value=hash_value).first()
    if not report:
        audit_logger.warning(f"Audit Tamper Alert: Verification FAILED for hash {hash_value} - IP: {request.remote_addr}")
        return render_template("verify_report.html", report=None, hash_value=hash_value), 404
        
    audit_logger.info(f"Audit Verification: Verified authenticity of Report {report.id} - Patient: {report.patient_name} - IP: {request.remote_addr}")
    return render_template("verify_report.html", report=report, hash_value=hash_value)


# =========================
# ANALYTICS DASHBOARD
# =========================

@app.route("/dashboard")
@login_required
@roles_accepted("admin", "doctor", "researcher")
def dashboard():
    """
    Clinical Analytics Dashboard UI
    ---
    tags:
      - Monitoring
    responses:
      200:
        description: Renders Chart.js analytics statistics.
    """
    return render_template("dashboard.html")


@app.route("/api/analytics")
@login_required
@roles_accepted("admin", "doctor", "researcher")
def api_analytics():
    """
    Clinical Analytics JSON Raw API
    ---
    tags:
      - Monitoring
    responses:
      200:
        description: Returns diagnosis distribution and confidence counts.
    """
    # Count disease predictions
    total_screenings = Report.query.count()
    
    normal_count = Report.query.filter(Report.disease.ilike("%normal%")).count()
    cataract_count = Report.query.filter(Report.disease.ilike("%cataract%")).count()
    glaucoma_count = Report.query.filter(Report.disease.ilike("%glaucoma%")).count()
    dr_count = Report.query.filter(Report.disease.ilike("%diabetic%")).count()
    
    # Calculate avg confidence
    avg_confidence = 0.0
    if total_screenings > 0:
        avg_confidence = db.session.query(db.func.avg(Report.confidence)).scalar() or 0.0
        
    # Get last 7 days screenings count
    screenings_by_day = []
    labels_by_day = []
    for i in range(6, -1, -1):
        day = datetime.datetime.utcnow().date() - datetime.timedelta(days=i)
        count = Report.query.filter(db.func.date(Report.timestamp) == day).count()
        labels_by_day.append(day.strftime("%b %d"))
        screenings_by_day.append(count)
        
    return {
        "total_screenings": total_screenings,
        "average_confidence": round(avg_confidence, 2),
        "disease_distribution": {
            "Normal": normal_count,
            "Cataract": cataract_count,
            "Glaucoma": glaucoma_count,
            "Diabetic Retinopathy": dr_count
        },
        "timeline": {
            "labels": labels_by_day,
            "data": screenings_by_day
        }
    }

# =========================
# MAIN
# =========================


if __name__ == "__main__":

    app.run(debug=True, port=8000)