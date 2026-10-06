import cv2
import numpy as np
import logging

logger = logging.getLogger("TcgSorter.Model.CardMatcher")


class CardMatcher:
    """
    Model component handling computer vision via OpenCV.
    Responsible for isolating, deskewing, and identifying cards from raw frames.
    """

    def __init__(self, target_width: int = 400, target_height: int = 560):
        # Standard aspect ratio for trading cards (approx. 2.5 x 3.5 inches)
        self.target_width = target_width
        self.target_height = target_height

    def extract_card(self, frame) -> np.ndarray:
        """
        Processes a raw frame, isolates the largest rectangular contour (the card),
        and applies a perspective warp to get a clean top-down view.
        :param frame: Raw image array from the camera view
        :return: Cropped, transformed card image, or None if extraction failed
        """
        if frame is None:
            return None

        # Step 1: Pre-processing for edge detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Step 2: Canny Edge Detection (adjust thresholds based on lighting if needed)
        edged = cv2.Canny(blurred, 30, 150)

        # Step 3: Find contours in the edged image
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            logger.warning("No contours found in the current frame.")
            return None

        # Sort contours by area to find the largest one (presumably the card)
        largest_contour = max(contours, key=cv2.contourArea)

        # Approximate the contour to a polygon to check if it's a rectangle
        peri = cv2.arcLength(largest_contour, True)
        approx = cv2.approxPolyDP(largest_contour, 0.02 * peri, True)

        # If our approximated polygon has exactly 4 points, we found a rectangle!
        if len(approx) == 4:
            logger.debug("Successfully isolated 4-point rectangular card contour.")
            return self._warp_perspective(frame, approx.reshape(4, 2))

        logger.warning("Largest contour is not rectangular. Card edge detection failed.")
        return None

    def _warp_perspective(self, frame: np.ndarray, pts: np.ndarray) -> np.ndarray:
        """
        Transforms a skewed quadrilateral into a clean, flat rectangle.
        """
        # Sum and difference to systematically identify corners
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)

        # Order: top-left, top-right, bottom-right, bottom-left
        rect = np.zeros((4, 2), dtype="float32")
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        # Destination coordinates for the flat top-down image
        dst = np.array([
                           [self.target_width - 1, 0],
                           [self.target_width - 1, self.target_height - 1],
                           [0, self.target_height - 1]
                           ], dtype="float32")

        # Calculate Perspective Transform Matrix and apply it
        matrix = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(frame, matrix, (self.target_width, self.target_height))

        return warped

    def identify(self, frame) -> str:
        """
        Placeholder for the next step: Perceptual Hashing or Feature Matching.
        Currently just extracts the card and checks if successful.
        """
        extracted = self.extract_card(frame)
        if extracted is not None:
            # For debugging, we could save the warped image here
            # cv2.imwrite("debug_extracted_card.png", extracted)
            return "SUCCESS"
        return "FAILED"
