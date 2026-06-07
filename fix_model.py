import tensorflow as tf
from tensorflow.keras.models import load_model

print("Loading old model...")

model = load_model(
    "model/retinal_5class.h5",
    compile=False,
    safe_mode=False
)

print("Saving fixed model...")

model.save(
    "model/fixed_retinal_model.h5"
)

print("DONE")