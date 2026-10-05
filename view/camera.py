import cv2


class Camera:
    """
    View component managing the optical sensor (Webcam) via OpenCV.
    Provides frames to the controller for subsequent model evaluation.
    """

    def __init__(self, camera_index: int = 0, width: int = 1280, height: int = 720):
        """
        Initializes the camera capture device settings.
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap = None

    def open(self) -> bool:
        """
        Opens the camera stream stream interface.
        :return: True if camera is ready for capturing
        """
        print(f"📷 Camera View: Opening stream on index {self.camera_index}...")
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            print("❌ Camera View Error: Stream initialization failed.")
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        return True

    def get_frame(self):
        """
        Grabs the current raw frame from the live video feed.
        :return: cv2 image frame numpy array, or None if reading failed
        """
        if self.cap is None or not self.cap.isOpened():
            print("❌ Camera View Warning: Attempted frame retrieval while camera is closed.")
            return None

        ret, frame = self.cap.read()
        if not ret:
            print("❌ Camera View Error: Failed to grab frame.")
            return None

        return frame

    def close(self):
        """
        Releases the webcam hardware and cleans up active resources.
        """
        if self.cap and self.cap.isOpened():
            self.cap.release()
            print("📷 Camera View: Resource released successfully.")
        cv2.destroyAllWindows()
