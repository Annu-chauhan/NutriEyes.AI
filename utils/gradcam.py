import numpy as np
import tensorflow as tf
import cv2
import os

from tensorflow.keras.preprocessing import image


def generate_gradcam(model, img_path, save_path):

    # =========================
    # LOAD IMAGE
    # =========================

    img = image.load_img(
        img_path,
        target_size=(224, 224)
    )

    img_array = image.img_to_array(img)

    img_array = np.expand_dims(
        img_array,
        axis=0
    )

    img_array = img_array / 255.0

    # =========================
    # MANUAL LAST CONV LAYER
    # =========================

    last_conv_layer_name = None

    # FIND LAST VALID CONV LAYER

    for layer in reversed(model.layers):

        if "conv" in layer.name.lower():

            last_conv_layer_name = layer.name

            break

    print(
        "\nUsing Layer:",
        last_conv_layer_name
    )

    if last_conv_layer_name is None:

        raise Exception(
            "No Conv Layer Found"
        )

    # =========================
    # CREATE MODEL
    # =========================

    grad_model = tf.keras.models.Model(

        inputs=model.inputs,

        outputs=[

            model.get_layer(
                last_conv_layer_name
            ).output,

            model.output
        ]
    )

    # =========================
    # GRADIENT CALCULATION
    # =========================

    with tf.GradientTape() as tape:

        conv_outputs, predictions = grad_model(
            img_array
        )

        pred_index = tf.argmax(
            predictions[0]
        )

        loss = predictions[:, pred_index]

    grads = tape.gradient(
        loss,
        conv_outputs
    )

    if grads is None:

        raise Exception(
            "Gradients are None"
        )

    # =========================
    # CREATE HEATMAP
    # =========================

    pooled_grads = tf.reduce_mean(
        grads,
        axis=(0, 1, 2)
    )

    conv_outputs = conv_outputs[0]

    heatmap = tf.reduce_sum(
        pooled_grads * conv_outputs,
        axis=-1
    )

    heatmap = np.maximum(
        heatmap,
        0
    )

    max_val = np.max(heatmap)

    if max_val != 0:

        heatmap /= max_val

    # =========================
    # ORIGINAL IMAGE
    # =========================

    original_img = cv2.imread(img_path)

    original_img = cv2.resize(
        original_img,
        (224, 224)
    )

    # =========================
    # HEATMAP PROCESS
    # =========================

    heatmap = cv2.resize(
        heatmap.numpy(),
        (224, 224)
    )

    heatmap = np.uint8(
        heatmap * 255
    )

    heatmap = cv2.applyColorMap(
        heatmap,
        cv2.COLORMAP_JET
    )

    # =========================
    # OVERLAY
    # =========================

    superimposed_img = cv2.addWeighted(

        original_img,
        0.6,

        heatmap,
        0.4,

        0
    )

    # =========================
    # SAVE IMAGE
    # =========================

    os.makedirs(
        "static/uploads",
        exist_ok=True
    )

    cv2.imwrite(
        save_path,
        superimposed_img
    )

    print(
        "\nGradCAM Saved:",
        save_path
    )

    return save_path