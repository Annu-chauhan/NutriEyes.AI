import os
import tensorflow as tf

from tensorflow.keras import layers
from tensorflow.keras import models

from tensorflow.keras.applications import MobileNetV2

from tensorflow.keras.preprocessing import image_dataset_from_directory

# =========================
# CONFIGURATION
# =========================

DATA_DIR = r"D:\NutriEye\dataset"

IMG_SIZE = (224, 224)

BATCH_SIZE = 32

EPOCHS = 25

MODEL_DIR = "model"

# =========================
# CREATE MODEL DIRECTORY
# =========================

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)

# =========================
# LOAD DATASETS
# =========================

train_ds = image_dataset_from_directory(

    DATA_DIR,

    validation_split=0.2,

    subset="training",

    seed=42,

    image_size=IMG_SIZE,

    batch_size=BATCH_SIZE,

    shuffle=True
)

val_ds = image_dataset_from_directory(

    DATA_DIR,

    validation_split=0.2,

    subset="validation",

    seed=42,

    image_size=IMG_SIZE,

    batch_size=BATCH_SIZE,

    shuffle=True
)

# =========================
# CLASS INFORMATION
# =========================

class_names = train_ds.class_names

num_classes = len(class_names)

print("\nDetected Classes:")
print(class_names)

print("\nNumber of Classes:")
print(num_classes)

# =========================
# PERFORMANCE OPTIMIZATION
# =========================

AUTOTUNE = tf.data.AUTOTUNE

train_ds = train_ds.prefetch(
    buffer_size=AUTOTUNE
)

val_ds = val_ds.prefetch(
    buffer_size=AUTOTUNE
)

# =========================
# DATA AUGMENTATION
# =========================

data_augmentation = tf.keras.Sequential([

    layers.RandomFlip("horizontal"),

    layers.RandomRotation(0.1),

    layers.RandomZoom(0.1)

])

# =========================
# LOAD PRETRAINED MODEL
# =========================

base_model = MobileNetV2(

    input_shape=(224, 224, 3),

    include_top=False,

    weights="imagenet"
)

# Fine-tune entire model

base_model.trainable = True

# =========================
# BUILD FINAL MODEL
# =========================

model = models.Sequential([

    layers.Input(shape=(224, 224, 3)),

    layers.Rescaling(1./255),

    data_augmentation,

    base_model,

    layers.GlobalAveragePooling2D(),

    layers.Dense(
        256,
        activation="relu"
    ),

    layers.Dropout(0.3),

    layers.Dense(
        num_classes,
        activation="softmax"
    )
])

# =========================
# BUILD MODEL
# =========================

model.build(
    (None, 224, 224, 3)
)

# =========================
# COMPILE MODEL
# =========================

model.compile(

    optimizer=tf.keras.optimizers.Adam(
        learning_rate=0.0001
    ),

    loss="sparse_categorical_crossentropy",

    metrics=["accuracy"]
)

# =========================
# MODEL SUMMARY
# =========================

model.summary()

# =========================
# CHECKPOINT
# =========================

checkpoint = tf.keras.callbacks.ModelCheckpoint(

    "model/best_retinal_model.h5",

    monitor="val_accuracy",

    save_best_only=True,

    mode="max",

    verbose=1
)

# =========================
# TRAIN MODEL
# =========================

history = model.fit(

    train_ds,

    validation_data=val_ds,

    epochs=EPOCHS,

    callbacks=[checkpoint]
)

# =========================
# SAVE FULL MODEL
# =========================

model.save(
    "model/retinal_5class.h5"
)

# =========================
# SAVE KERAS MODEL
# =========================

model.save(
    "model/retinal_5class.keras"
)

# =========================
# SAVE WEIGHTS
# =========================

model.save_weights(
    "model/retinal_5class.weights.h5"
)

print("\n===================================")
print("MODEL TRAINING COMPLETED")
print("MODEL SAVED SUCCESSFULLY")
print("===================================")