from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image_dataset_from_directory

model = load_model("model/retinal_5class.h5")

val_ds = image_dataset_from_directory(
    "dataset",
    validation_split=0.2,
    subset="validation",
    seed=42,
    image_size=(224, 224),
    batch_size=32
)

loss, acc = model.evaluate(val_ds)

print("\nValidation Accuracy =", round(acc * 100, 2), "%")