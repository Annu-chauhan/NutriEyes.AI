from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np

model = load_model(
    "model/retinal_5class.h5",
    compile=False
)

class_names = [
    "cataract",
    "diabetic_retinopathy",
    "glaucoma",
    "normal"
]

img = image.load_img(
    "dataset/normal/939_right.jpg",
    target_size=(224,224)
)

img_array = image.img_to_array(img)

img_array = np.expand_dims(img_array, axis=0)

prediction = model.predict(img_array)

print(prediction)

for i,p in enumerate(prediction[0]):
    print(class_names[i], round(float(p)*100,2), "%")

print(
    "Predicted:",
    class_names[np.argmax(prediction)]
)
