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

print("Retina model loaded successfully")

# =========================
# LOAD TRAINED MODEL
# =========================

model = load_model("retinal_5class.keras")
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

    "Retinal Disease"
]

# =========================
# VALIDATE IMAGE
# =========================

def validate_retina_image(filepath):

    try:

        img = Image.open(filepath)

        img.verify()

        return True, "Valid image"

    except Exception as e:

        return False, f"Invalid image: {str(e)}"

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
    # NORMALIZE IMAGE
    # =========================

    img_array = img_array / 255.0

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
    # EXPAND DIMENSIONS
    # =========================

    img_array = np.expand_dims(

        img_array,

        axis=0
    )

    # =========================
    # MODEL PREDICTION
    # =========================

    prediction = model.predict(
        img_array
    )

    print(
        "\nRaw Prediction:",
        prediction,
        "\n"
    )

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

    gradcam_path = os.path.join(

        "static",

        "uploads",

        "gradcam.jpg"
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