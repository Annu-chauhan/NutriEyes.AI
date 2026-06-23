import os
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# =========================
# 📌 CONFIG
# =========================
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 15
NUM_CLASSES = 5

DATASET_PATH = "dataset"  # change this to your dataset folder

# 🔥 CHANGE MODEL HERE
MODEL_NAME = "efficientnet"   # vgg16 / mobilenet / resnet / densenet / efficientnet

# =========================
# 📂 DATA GENERATOR
# =========================
train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=15,
    zoom_range=0.1,
    horizontal_flip=True,
    validation_split=0.2
)

train_data = train_datagen.flow_from_directory(
    DATASET_PATH,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    subset='training'
)

val_data = train_datagen.flow_from_directory(
    DATASET_PATH,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    subset='validation'
)

# =========================
# 🧠 BASE MODEL SELECTION
# =========================
def get_base_model(name):
    if name == "vgg16":
        from tensorflow.keras.applications import VGG16
        from tensorflow.keras.applications.vgg16 import preprocess_input
        base_model = VGG16(input_shape=(224,224,3), include_top=False, weights='imagenet')

    elif name == "mobilenet":
        from tensorflow.keras.applications import MobileNetV2
        from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
        base_model = MobileNetV2(input_shape=(224,224,3), include_top=False, weights='imagenet')

    elif name == "resnet":
        from tensorflow.keras.applications import ResNet50
        from tensorflow.keras.applications.resnet50 import preprocess_input
        base_model = ResNet50(input_shape=(224,224,3), include_top=False, weights='imagenet')

    elif name == "densenet":
        from tensorflow.keras.applications import DenseNet121
        from tensorflow.keras.applications.densenet import preprocess_input
        base_model = DenseNet121(input_shape=(224,224,3), include_top=False, weights='imagenet')

    else:  # efficientnet
        from tensorflow.keras.applications import EfficientNetB0
        from tensorflow.keras.applications.efficientnet import preprocess_input
        base_model = EfficientNetB0(input_shape=(224,224,3), include_top=False, weights='imagenet')

    return base_model, preprocess_input

base_model, preprocess_input = get_base_model(MODEL_NAME)

# Freeze base model (transfer learning)
for layer in base_model.layers:
    layer.trainable = False

# =========================
# 🏗️ CUSTOM HEAD
# =========================
x = base_model.output
x = layers.GlobalAveragePooling2D()(x)
x = layers.BatchNormalization()(x)
x = layers.Dense(256, activation='relu')(x)
x = layers.Dropout(0.5)(x)
output = layers.Dense(NUM_CLASSES, activation='softmax')(x)

model = models.Model(inputs=base_model.input, outputs=output)

# =========================
# ⚙️ COMPILE
# =========================
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

model.summary()

# =========================
# 📉 CALLBACKS
# =========================
callbacks = [
    tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
    tf.keras.callbacks.ReduceLROnPlateau(patience=3, factor=0.2),
    tf.keras.callbacks.ModelCheckpoint(
        f"{MODEL_NAME}_best.h5",
        save_best_only=True,
        monitor='val_accuracy'
    )
]

# =========================
# 🚀 TRAIN
# =========================
history = model.fit(
    train_data,
    validation_data=val_data,
    epochs=EPOCHS,
    callbacks=callbacks
)

# =========================
# 💾 SAVE MODEL
# =========================
model.save(f"{MODEL_NAME}_final.h5")

print("✅ Training Complete!")