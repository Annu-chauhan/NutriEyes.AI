# NutriEye – AI-Based Multi-Class Retinal Disease Detection System

## Overview

NutriEye is an AI-powered healthcare web application designed to detect multiple retinal diseases using Deep Learning and Transfer Learning techniques. The system analyzes retinal fundus images and predicts retinal diseases with confidence scores, helping in early diagnosis and clinical decision support.

The project integrates:

* Deep Learning for retinal disease classification
* Transfer Learning using CNN architectures
* Flask-based web application
* Confidence-based prediction system
* Secure patient data handling
* Clinical recommendation support

---

# Features

* Multi-class retinal disease detection
* Upload retinal fundus image
* AI-based disease prediction
* Confidence score generation
* Clinical recommendation support
* Modern web interface
* Deep learning model integration
* Image validation system
* Healthcare-focused workflow

---

# Diseases Detected

The current model can classify:

1. Cataract
2. Diabetic Retinopathy
3. Glaucoma
4. Normal Retina
5. Retinal Disease

---

# Tech Stack

## Frontend

* HTML
* CSS
* Bootstrap
* JavaScript

## Backend

* Python
* Flask

## Deep Learning

* TensorFlow
* Keras
* Transfer Learning
* CNN

## Database (Optional)

* MySQL

---

# Project Structure

```bash
NutriEye/
│
├── app.py
├── requirements.txt
├── README.md
│
├── model/
│   └── retinal_5class.h5
│
├── static/
│   ├── css/
│   ├── js/
│   ├── uploads/
│   └── results/
│
├── templates/
│   ├── index.html
│   ├── result.html
│   └── about.html
│
├── utils/
│   ├── predict.py
│   └── preprocess.py
│
└── dataset/
```

---

# Installation

## Step 1: Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/NutriEye.git
```

## Step 2: Move to Project Directory

```bash
cd NutriEye
```

## Step 3: Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux/Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

# Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Run Application

```bash
python app.py
```

Application will run on:

```bash
http://127.0.0.1:5000/
```

---

# Model Details

* Framework: TensorFlow/Keras
* Architecture: CNN + Transfer Learning
* Input: Retinal Fundus Image
* Output: Disease Prediction + Confidence Score
* Classes: 5

---

# Dataset

The dataset contains retinal fundus images collected and preprocessed for multi-class classification.

## Dataset Preprocessing

* Image resizing
* Normalization
* Data augmentation
* Noise reduction
* Class balancing

---

# Future Enhancements

* Blockchain-based medical record security
* Doctor appointment integration
* Real-time screening system
* Mobile application
* Cloud deployment
* Explainable AI visualization
* PDF medical report generation

---

# Screenshots

## Home Page

(Add Screenshot Here)

## Prediction Result

(Add Screenshot Here)

## Upload Page

(Add Screenshot Here)

---

# Research Contribution

This project focuses on:

* Early retinal disease diagnosis
* AI-assisted healthcare
* Clinical decision support systems
* Transfer learning optimization
* Medical image analysis

---

# Authors

## Team NutriEye

* Parul Chauhan
* Nandan Kumar
* Mohamemad Khan

Department of Computer Science & Engineering
Galgotias University

---

# License

This project is developed for educational and research purposes.

---

# GitHub Push Commands

## Initialize Git

```bash
git init
```

## Add Files

```bash
git add .
```

## Commit Files

```bash
git commit -m "Initial commit - NutriEye project"
```

## Create Main Branch

```bash
git branch -M main
```

## Connect GitHub Repository

```bash
git remote add origin https://github.com/YOUR_USERNAME/NutriEye.git
```

## Push to GitHub

```bash
git push -u origin main
```

---

