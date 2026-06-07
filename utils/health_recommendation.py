HEALTH_RECOMMENDATIONS = {

    "Cataract": {

        "description":
        "Cataract is a clouding of the eye lens that can reduce vision clarity over time.",

        "diet": [
            "Increase Vitamin C rich foods",
            "Consume carrots and citrus fruits",
            "Eat leafy green vegetables",
            "Avoid smoking and excessive alcohol"
        ],

        "exercise": [
            "Daily walking for 30 minutes",
            "Eye focus exercises",
            "Light stretching exercises"
        ],

        "yoga": [
            "Trataka",
            "Deep breathing exercises",
            "Meditation"
        ],

        "precautions": [
            "Wear UV protection sunglasses",
            "Avoid prolonged screen exposure",
            "Maintain regular eye checkups"
        ],

        "doctor":
        "Consult an ophthalmologist for cataract evaluation."
    },

    "Diabetic Retinopathy": {

        "description":
        "Diabetic Retinopathy occurs due to retinal blood vessel damage caused by diabetes.",

        "diet": [
            "Reduce sugar intake",
            "Increase leafy green vegetables",
            "Consume omega-3 rich foods",
            "Maintain a balanced diabetic-friendly diet"
        ],

        "exercise": [
            "Light cardio exercises",
            "Daily walking",
            "Blood sugar monitoring exercises"
        ],

        "yoga": [
            "Anulom Vilom",
            "Bhramari Pranayama",
            "Meditation"
        ],

        "precautions": [
            "Monitor blood glucose regularly",
            "Avoid smoking",
            "Schedule regular retinal screening"
        ],

        "doctor":
        "Consult a retina specialist immediately."
    },

    "Glaucoma": {

        "description":
        "Glaucoma is an eye condition that damages the optic nerve and may lead to vision loss.",

        "diet": [
            "Consume antioxidant-rich foods",
            "Increase Vitamin A intake",
            "Stay hydrated",
            "Eat green leafy vegetables"
        ],

        "exercise": [
            "Light aerobic exercise",
            "Eye relaxation exercises",
            "Daily walking"
        ],

        "yoga": [
            "Palming exercise",
            "Meditation",
            "Deep breathing"
        ],

        "precautions": [
            "Avoid high eye pressure activities",
            "Maintain proper sleep",
            "Regular eye pressure evaluation"
        ],

        "doctor":
        "Schedule glaucoma pressure evaluation with an ophthalmologist."
    },

    "Normal": {

        "description":
        "No major retinal abnormality was detected in the uploaded retinal image.",

        "diet": [
            "Maintain balanced nutrition",
            "Consume fruits and vegetables",
            "Drink adequate water"
        ],

        "exercise": [
            "Regular physical activity",
            "Walking and stretching"
        ],

        "yoga": [
            "Eye relaxation yoga",
            "Meditation",
            "Breathing exercises"
        ],

        "precautions": [
            "Avoid excessive screen exposure",
            "Maintain healthy lifestyle habits",
            "Routine annual eye checkups"
        ],

        "doctor":
        "Continue regular annual eye checkups."
    },

    "Retinal Detachment": {

        "description":
        "Retinal Detachment is a serious retinal condition requiring immediate medical attention.",

        "diet": [
            "Maintain a healthy antioxidant-rich diet",
            "Consume Vitamin A and omega-3 foods",
            "Eat nutrient-rich vegetables"
        ],

        "exercise": [
            "Avoid heavy physical strain",
            "Follow specialist guidance"
        ],

        "yoga": [
            "Light breathing exercises only"
        ],

        "precautions": [
            "Avoid sudden head movements",
            "Seek emergency medical attention immediately"
        ],

        "doctor":
        "Seek emergency retinal specialist consultation immediately."
    }
}


# =========================
# GET RECOMMENDATION
# =========================

def get_health_recommendation(disease):

    return HEALTH_RECOMMENDATIONS.get(

        disease,

        {

            "description":
            "No detailed recommendation available.",

            "diet": [],

            "exercise": [],

            "yoga": [],

            "precautions": [],

            "doctor":
            "Consult an ophthalmologist."
        }
    )