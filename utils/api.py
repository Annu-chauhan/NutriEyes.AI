def get_ai_response(disease, severity):
    return f"""
Based on the image analysis, NutriEye detected possible signs of {disease} with {severity} severity.

Suggested next steps:
- Visit an ophthalmologist for proper confirmation
- Maintain a diet rich in Vitamin A, antioxidants, Omega-3, and leafy vegetables
- Reduce eye strain from long screen exposure
- Schedule periodic eye checkups
"""