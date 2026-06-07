import cv2
import os

# =========================
# CAMERA FUNCTION
# =========================

def capture_eye_image():

    # =========================
    # CREATE SAVE DIRECTORY
    # =========================

    save_dir = os.path.join(
        "static",
        "uploads"
    )

    os.makedirs(
        save_dir,
        exist_ok=True
    )

    # =========================
    # START CAMERA
    # =========================

    cam = cv2.VideoCapture(0)

    # =========================
    # HD CAMERA SETTINGS
    # =========================

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # =========================
    # LOAD EYE CASCADE
    # =========================

    eye_cascade = cv2.CascadeClassifier(

        cv2.data.haarcascades
        + "haarcascade_eye.xml"
    )

    # =========================
    # CAMERA CHECK
    # =========================

    if not cam.isOpened():

        print("Camera not accessible")

        return None

    # =========================
    # CAMERA LOOP
    # =========================

    while True:

        ret, frame = cam.read()

        if not ret:

            break

        # =========================
        # FLIP CAMERA
        # =========================

        frame = cv2.flip(
            frame,
            1
        )

        # =========================
        # CONVERT TO GRAYSCALE
        # =========================

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        # =========================
        # DETECT EYES
        # =========================

        eyes = eye_cascade.detectMultiScale(

            gray,

            scaleFactor=1.3,

            minNeighbors=5
        )

        # =========================
        # DRAW RECTANGLES
        # =========================

        for (x, y, w, h) in eyes:

            cv2.rectangle(

                frame,

                (x, y),

                (x + w, y + h),

                (0, 255, 0),

                2
            )

        # =========================
        # SCREEN TEXT
        # =========================

        cv2.putText(

            frame,

            "SPACE = Capture | ESC = Exit",

            (20, 40),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.8,

            (0, 255, 0),

            2
        )

        # =========================
        # SHOW CAMERA
        # =========================

        cv2.imshow(
            "NutriEye Live Camera",
            frame
        )

        key = cv2.waitKey(1)

        # =========================
        # ESC TO EXIT
        # =========================

        if key % 256 == 27:

            print("Camera closed")

            break

        # =========================
        # SPACE TO CAPTURE
        # =========================

        elif key % 256 == 32:

            save_path = os.path.join(

                save_dir,

                "captured_eye.jpg"
            )

            # =========================
            # SAVE EYE REGION
            # =========================

            if len(eyes) > 0:

                x, y, w, h = eyes[0]

                eye_img = frame[
                    y:y+h,
                    x:x+w
                ]

                cv2.imwrite(
                    save_path,
                    eye_img
                )

            else:

                cv2.imwrite(
                    save_path,
                    frame
                )

            print(
                "Image saved:",
                save_path
            )

            cam.release()

            cv2.destroyAllWindows()

            return save_path

    # =========================
    # CLEANUP
    # =========================

    cam.release()

    cv2.destroyAllWindows()

    return None