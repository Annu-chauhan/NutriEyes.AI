import os
import numpy as np

from PIL import Image

from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

from utils.health_recommendation import (
    get_health_recommendation
)

from utils.gradcam import (
    generate_gradcam
)

print("Retina model loading...")

MODEL_PATH = os.path.join(
    "model",
    "retinal_5class.h5"
)

print("Using local model:", MODEL_PATH)

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model not found: {MODEL_PATH}"
    )

model = load_model(
    MODEL_PATH,
    compile=False
)

print("Retina model loaded successfully")
# =========================
# MODEL INFO
# =========================

print(
    "Model Output Shape:",
    model.output_shape
)

# =========================
# CLASS LABELS
# =========================

class_labels = [
    "Cataract",
    "Diabetic Retinopathy",
    "Glaucoma",
    "Normal",
    
]

# =========================
# VALIDATE IMAGE
# =========================

def validate_retina_image(filepath):
    try:
        # 1. Check file extension
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png"]:
            return False, "Unsupported file extension. Only JPG, JPEG, and PNG are allowed."

        # 2. Check file size (5 MB limit)
        file_size = os.path.getsize(filepath)
        if file_size > 5 * 1024 * 1024:
            return False, "File size exceeds the 5 MB security limit."

        # 3. Check magic bytes signature
        with open(filepath, "rb") as f:
            header = f.read(8)
        
        if ext in [".jpg", ".jpeg"]:
            # JPEG start bytes: FF D8 FF
            if not header.startswith(b"\xff\xd8\xff"):
                return False, "Malformed JPEG: file signature mismatch."
        elif ext == ".png":
            # PNG start bytes: 89 50 4E 47 0D 0A 1A 0A
            if not header.startswith(b"\x89PNG\r\n\x1a\n"):
                return False, "Malformed PNG: file signature mismatch."

        # 4. Verify image using PIL
        img = Image.open(filepath)
        img.verify()
        return True, "Valid image"

    except Exception as e:
        return False, f"Invalid image file: {str(e)}"

# =========================
# CONFIDENCE LEVEL
# =========================

def get_confidence_level(confidence):

    if confidence < 40:

        return "Low Confidence"

    elif confidence < 55:

        return "Moderate Confidence"

    elif confidence < 75:

        return "Good Confidence"

    else:

        return "High Confidence"

# =========================
# PREDICT DISEASE
# =========================

def predict_disease(filepath):

    # =========================
    # LOAD IMAGE
    # =========================

    img = image.load_img(

        filepath,

        target_size=(224, 224)
    )

    # =========================
    # IMAGE ARRAY
    # =========================

    img_array = image.img_to_array(img)

    # =========================
    # INVALID IMAGE CHECK
    # =========================

    img_check = np.mean(img_array)

    if img_check < 0.05:

        return {

            "disease": "Invalid Retina Scan",

            "confidence": 0,

            "confidence_level": "Invalid",

            "prediction": [],

            "top2_predictions": [],

            "recommendation": {

                "description":
                "Image not suitable for retinal diagnosis.",

                "diet": [],

                "exercise": [],

                "yoga": [],

                "precautions": [],

                "doctor":
                "Please upload retinal fundus scan."
            },

            "gradcam_image": None
        }

    # =========================
# NORMALIZE IMAGE
# =========================

    
    

# =========================
# EXPAND DIMENSIONS
# =========================

    img_array = np.expand_dims(
    img_array,
    axis=0
)

    # =========================
    # MODEL PREDICTION
    # =========================

    prediction = model.predict(img_array)

    print("\n========== PREDICTION ==========")
    print(prediction)

    for i, p in enumerate(prediction[0]):
        print(
        class_labels[i],
        "=",
        round(float(p) * 100, 2),
        "%"
    )

    print(
    "Predicted:",
    class_labels[np.argmax(prediction)]
)

    print("================================\n")

    # =========================
    # BEST CLASS
    # =========================

    idx = np.argmax(
        prediction
    )

    disease = class_labels[idx]

    # =========================
    # CONFIDENCE
    # =========================

    confidence = float(

        np.max(prediction) * 100
    )

    confidence_level = get_confidence_level(
        confidence
    )

    # =========================
    # HEALTH RECOMMENDATION
    # =========================

    recommendation = get_health_recommendation(
        disease
    )

    # =========================
    # TOP 2 PREDICTIONS
    # =========================

    top2_idx = prediction[0].argsort()[-2:][::-1]

    top2_predictions = []

    for i in top2_idx:

        top2_predictions.append({

            "disease": class_labels[i],

            "confidence": round(

                float(
                    prediction[0][i] * 100
                ),

                2
            )
        })

    # =========================
    # CREATE GRADCAM FOLDER
    # =========================

    os.makedirs(
        os.path.join(
            "static",
            "uploads"
        ),
        exist_ok=True
    )

    # =========================
    # GRADCAM PATH
    # =========================

    base_filename = os.path.basename(filepath)

    gradcam_path = os.path.join(

        "static",

        "uploads",

        f"gradcam_{base_filename}"
    )

    # =========================
    # GENERATE GRADCAM
    # =========================

    try:

        returned_path = generate_gradcam(

            model,

            filepath,

            gradcam_path
        )

        print(
            "\nReturned GradCAM Path:",
            returned_path
        )

        # =========================
        # VERIFY FILE EXISTS
        # =========================

        if returned_path and os.path.exists(returned_path):

            print(
                "\nGradCAM generated successfully\n"
            )

            gradcam_path = returned_path

        else:

            print(
                "\nGradCAM image NOT found after generation\n"
            )

            gradcam_path = None

    except Exception as e:

        import traceback

        print("\n========== GRADCAM ERROR ==========\n")

        traceback.print_exc()

        print("\nERROR MESSAGE:\n")

        print(str(e))

        print("\n===================================\n")

        gradcam_path = None

    # =========================
    # FINAL RESPONSE
    # =========================

    return {

        "disease": disease,

        "confidence": round(
            confidence,
            2
        ),

        "confidence_level": confidence_level,

        "prediction": prediction.tolist(),

        "top2_predictions": top2_predictions,

        "recommendation": recommendation,

        "gradcam_image":

            "/" + gradcam_path.replace("\\", "/")

            if gradcam_path

            else None
    }