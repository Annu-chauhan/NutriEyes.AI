def get_disease_info(disease_name):
    disease_data = {
        "Normal": {
            "description": "No major retinal disease detected.",
            "treatment": "No treatment required.",
            "precautions": "Maintain a healthy lifestyle and get regular eye checkups."
        },
        "Cataract": {
            "description": "Cataract causes clouding of the eye lens, affecting vision.",
            "treatment": "Surgery is the most common and effective treatment.",
            "precautions": "Wear UV-protected glasses and avoid smoking."
        },
        "Diabetic Retinopathy": {
            "description": "A diabetes complication that affects the retina.",
            "treatment": "Blood sugar control, laser treatment, or injections.",
            "precautions": "Monitor blood sugar and get regular eye exams."
        },
        "Glaucoma": {
            "description": "A condition that damages the optic nerve due to high eye pressure.",
            "treatment": "Eye drops, medicines, laser treatment, or surgery.",
            "precautions": "Regular eye pressure checks and avoid stress."
        },
        "Other": {
            "description": "An unspecified retinal or eye-related condition.",
            "treatment": "Consult an eye specialist for diagnosis and treatment.",
            "precautions": "Do not ignore symptoms and get a professional eye exam."
        }
    }

    return disease_data.get(disease_name, {
        "description": "No disease information available.",
        "treatment": "Consult a doctor.",
        "precautions": "Follow proper eye care and regular checkups."
    })