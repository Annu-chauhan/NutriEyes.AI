import numpy as np
import cv2
import os


def generate_gradcam(model, img_path, save_path):

    import tensorflow as tf
    from tensorflow.keras.preprocessing import image

    # =========================
    # LOAD IMAGE
    # =========================

    img = image.load_img(
        img_path,
        target_size=(224, 224)
    )

    img_array = image.img_to_array(img)

    # Do not manually divide by 255 here, because the outer model has Rescaling(1./255) layer 0.
    img_array = np.expand_dims(
        img_array,
        axis=0
    )

    # =========================
    # FIND MOBILENET MODEL
    # =========================

    base_model = None

    for layer in model.layers:

        if "mobilenet" in layer.name.lower():

            base_model = layer

            break

    if base_model is None:

        raise Exception(
            "MobileNetV2 layer not found"
        )

    # =========================
    # LAST CONV LAYER
    # =========================

    last_conv_layer = None

    for layer in reversed(base_model.layers):

        if isinstance(
            layer,
            tf.keras.layers.Conv2D
        ):

            last_conv_layer = layer.name

            break

    print(
        "\nUsing Layer:",
        last_conv_layer
    )

    if last_conv_layer is None:

        raise Exception(
            "No Conv Layer Found"
        )

    # =========================
    # BUILD MULTI-OUTPUT BASE MODEL
    # =========================

    base_model_multi = tf.keras.models.Model(
        inputs=base_model.input,
        outputs=[
            base_model.get_layer(last_conv_layer).output,
            base_model.output
        ]
    )

    # =========================
    # GRADIENTS WITH SEQUENTIAL FORWARD PASS
    # =========================

    with tf.GradientTape() as tape:

        # Layer 0: Rescaling
        x = model.layers[0](img_array)

        # Layer 1: Data Augmentation
        x = model.layers[1](x, training=False)

        # Pass to MobileNetV2 and watch conv_outputs
        conv_outputs, base_out = base_model_multi(x)
        tape.watch(conv_outputs)

        # Layer 3: GlobalAveragePooling2D
        x = model.layers[3](base_out)

        # Layer 4: Dense
        x = model.layers[4](x)

        # Layer 5: Dropout
        x = model.layers[5](x, training=False)

        # Layer 6: Dense (final softmax output)
        predictions = model.layers[6](x)

        pred_index = tf.argmax(predictions[0])

        loss = predictions[:, pred_index]

    grads = tape.gradient(
        loss,
        conv_outputs
    )

    pooled_grads = tf.reduce_mean(
        grads,
        axis=(0, 1, 2)
    )

    conv_outputs = conv_outputs[0]

    heatmap = tf.reduce_sum(
        pooled_grads * conv_outputs,
        axis=-1
    )

    # Convert to numpy before using numpy functions
    heatmap = heatmap.numpy()

    heatmap = np.maximum(
        heatmap,
        0
    )

    heatmap /= (
        np.max(heatmap) + 1e-8
    )

    # =========================
    # ORIGINAL IMAGE
    # =========================

    original_img = cv2.imread(
        img_path
    )

    original_img = cv2.resize(
        original_img,
        (224, 224)
    )

    # =========================
    # HEATMAP
    # =========================

    heatmap = cv2.resize(
        heatmap,
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
    # SAVE
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