import cv2
import numpy as np
import logging
import os
import imagehash
from PIL import Image

logger = logging.getLogger("TcgSorter.Model.CardMatcher")


class CardMatcher:
    """
    Model component handling computer vision via OpenCV and Image Hashing.
    Responsible for isolating cards and matching them against a reference database.
    """

    def __init__(self, reference_dir: str = "reference_cards", target_width: int = 400, target_height: int = 560):
        self.target_width = target_width
        self.target_height = target_height
        self.reference_dir = reference_dir

        # In-memory database for reference hashes: {card_name: hash_object}
        self.reference_db = {}

        # Ensure the reference directory exists and load hashes
        if not os.path.exists(self.reference_dir):
            os.makedirs(self.reference_dir)
            logger.info(f"Created empty reference directory at '{self.reference_dir}'. Add reference images there!")
        else:
            self.load_reference_images()

    def load_reference_images(self):
        """
        Scans the reference directory, computes pHashes for all images,
        and stores them in the local database.
        """
        self.reference_db.clear()
        supported_extensions = (".png", ".jpg", ".jpeg", ".webp")

        for filename in os.listdir(self.reference_dir):
            if filename.lower().endswith(supported_extensions):
                path = os.path.join(self.reference_dir, filename)
                try:
                    # Load image via OpenCV, convert to RGB, then to PIL Image for imagehash
                    cv_img = cv2.imread(path)
                    rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb_img)

                    # Compute perceptual hash
                    img_hash = imagehash.phash(pil_img)

                    # Use filename (without extension) as the card identity name
                    card_name = os.path.splitext(filename)[0]
                    self.reference_db[card_name] = img_hash
                    logger.debug(f"Loaded reference card: '{card_name}' with hash {img_hash}")
                except Exception as e:
                    logger.error(f"Failed to process reference image {filename}: {e}")

        logger.info(f"📚 CardMatcher: Successfully indexed {len(self.reference_db)} reference cards.")

    def extract_card(self, frame) -> np.ndarray:
        """
        Processes a raw frame, isolates the largest rectangular contour (the card),
        and applies a perspective warp to get a clean top-down view.
        """
        if frame is None:
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 30, 150)

        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest_contour = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(largest_contour, True)
        approx = cv2.approxPolyDP(largest_contour, 0.02 * peri, True)

        if len(approx) == 4:
            return self._warp_perspective(frame, approx.reshape(4, 2))
        return None

    def _warp_perspective(self, frame: np.ndarray, pts: np.ndarray) -> np.ndarray:
        """
        Transforms a skewed quadrilateral into a clean, flat rectangle.
        """
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)

        rect = np.zeros((4, 2), dtype="float32")
        rect[0] = pts[np.argmin(s)]  # Top-Left
        rect[2] = pts[np.argmax(s)]  # Bottom-Right
        rect[1] = pts[np.argmin(diff)]  # Top-Right
        rect[3] = pts[np.argmax(diff)]  # Bottom-Left

        dst = np.array([
                           [self.target_width - 1, 0],
                           [self.target_width - 1, self.target_height - 1],
                           [0, self.target_height - 1]
                           ], dtype="float32")

        matrix = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(frame, matrix, (self.target_width, self.target_height))

    def identify_card_name(self, frame, threshold: int = 15) -> str:
        """
        Extracts the card from the frame, computes its pHash, and compares it
        against the reference database using Hamming Distance.
        :param frame: Raw webcam image
        :param threshold: Max allowed Hamming distance (lower means stricter match)
        :return: Name of the matched card file, or None if no close match found
        """
        extracted_card = self.extract_card(frame)
        if extracted_card == None:
            logger.warning("CV Pipeline: Could not find card edges in frame.")
            return None

        # Convert extracted OpenCV image to PIL format
        rgb_card = cv2.cvtColor(extracted_card, cv2.COLOR_BGR2RGB)
        pil_card = Image.fromarray(rgb_card)
        current_hash = imagehash.phash(pil_card)

        best_match = None
        lowest_distance = 999  # Start with an impossibly high Hamming distance

        # Compare current hash against all stored reference hashes
        for card_name, ref_hash in self.reference_db.items():
            # In imagehash, subtraction calculates the Hamming Distance
            distance = current_hash - ref_hash

            if distance < lowest_distance:
                lowest_distance = distance
                best_match = card_name

        logger.debug(f"Best match found: '{best_match}' with Hamming distance: {lowest_distance}")

        # If the closest match is within our acceptable error threshold, return it
        if lowest_distance <= threshold:
            logger.info(f"🎯 Successful Match: '{best_match}' (Distance: {lowest_distance})")
            return best_match

        logger.warning(f"Card detected, but lowest distance ({lowest_distance}) exceeded threshold ({threshold}).")
        return None
