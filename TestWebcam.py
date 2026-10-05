import cv2
import os


def main():
    print("==================================================")
    print("NXT TCG Sorter - Camera Setup & Capture Test")
    print("==================================================")

    # 0 is usually the built-in webcam, 1 or 2 is typically an external USB camera
    camera_index = 0

    print(f"Opening camera stream (Index: {camera_index})...")
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)  # CAP_DSHOW optimizes startup on Windows

    # Check if the webcam was successfully opened
    if not cap.isOpened():
        print("❌ ERROR: Could not open webcam.")
        print("Please check if the camera is connected or used by another app (e.g., Zoom/Teams).")
        return

    # Set resolution (optional, adjust depending on your camera capabilities)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("\n💡 Controls:")
    print("   [SPACE] -> Capture and save an image of the card")
    print("   [ESC]   -> Quit the application")
    print("--------------------------------------------------")

    img_counter = 0

    while True:
        # Capture frame-by-frame from the live stream
        ret, frame = cap.read()

        if not ret:
            print("❌ ERROR: Failed to grab frame.")
            break

        # Display the live video stream in a GUI window
        cv2.imshow("TCG Sorter - Camera Live Feed", frame)

        # Wait for 1 millisecond for a key press
        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            # ESC key pressed to exit
            print("Shutting down camera feed...")
            break

        elif key == 32:
            # SPACE key pressed to save the current frame
            img_name = f"captured_card_{img_counter}.png"

            # Save the image to the current project directory
            cv2.imwrite(img_name, frame)
            print(f"📸 Image saved successfully as: {img_name}")
            img_counter += 1

    # When everything done, release the capture and destroy all GUI windows
    cap.release()
    cv2.destroyAllWindows()
    print("==================================================")


if __name__ == "__main__":
    main()
