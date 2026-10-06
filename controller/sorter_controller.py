import time
import logging
import random
from typing import Optional

from model.sorter_state import SorterState
from model.card import Card, MtgCard, PokemonCard
from view.lego_hardware import LegoHardware
from view.camera import Camera
from model.card_matcher import CardMatcher

# Grab the sub-logger for the controller layer
logger = logging.getLogger("TcgSorter.Controller")


class SorterController:
    """
    The brain of the MVC architecture. Controls the state machine,
    reads sensor data from the Views, and updates the System Model.
    """

    def __init__(self, brick):
        # Initialize the Model components
        self.state = SorterState()
        self.matcher = CardMatcher()

        # Initialize the View components
        self.hardware = LegoHardware(brick)
        self.camera = Camera(camera_index=0)

        self.is_active = False
        logger.info("🎮 SorterController: MVC architecture layered successfully.")

    def _generate_mock_card(self):
        """
        Helper method to simulate image recognition results until
        the CardMatcher module is fully implemented.
        """
        tcg_pool = [
            lambda: MtgCard("Black Lotus", "001", "COLORLESS", "mythic", "0", "get 3 mana", "artefact"),
            lambda: MtgCard("Lightning Bolt", "124", "R", "common", "R", "Deal 3 damage", "instant"),
            lambda: MtgCard("Counterspell", "054", "B", "common", "B", "Counter target  Spell.", "instant"),
            lambda: PokemonCard("Charizard", "BS-4", "FIRE", "holo rare"),
            lambda: PokemonCard("Pikachu", "VIV-043", "LIGHTNING", "common"),
            lambda: PokemonCard("Professor's Research", "SSH-178", "TRAINER", "rare")
        ]
        return random.choice(tcg_pool)()

    def _process_and_identify_card(self, frame) -> Optional[Card]:
        """
        Private helper method to encapsulate the image extraction and identification pipeline.
        :param frame: The raw image frame from the camera view
        :return: A concrete Card object if successful, or None if extraction/matching fails
        """
        logger.debug("Passing frame data to CardMatcher algorithm...")
        match_status = self.matcher.identify(frame)

        if match_status == "FAILED":
            logger.warning("Card contours could not be extracted by OpenCV pipeline.")
            return None

        # If CV extraction worked, fall back to our safe mock generator for identification
        # TODO: Replace with real database/pHash lookup in the next milestone
        detected_card = self._generate_mock_card()
        logger.info(f"Card successfully matched: '{detected_card.get_name()}' ({type(detected_card).__name__})")
        return detected_card

    def start_sorting(self, max_cards: int = 5):
        """
        Starts the main processing loop of the robot.
        :param max_cards: Safety break condition to prevent infinite mechanical loops during testing
        """
        logger.info(f"🎮 Starting sorting process. Batch limit: {max_cards} cards.")

        if not self.camera.open():
            logger.critical("Aborting sorting loop: Camera view could not be initialized.")
            return

        self.state.start_session()
        self.is_active = True
        card_counter = 0

        try:
            while self.is_active and card_counter < max_cards:
                card_counter += 1
                logger.info(f"--- Processing Card Lifecycle #{card_counter} ---")

                # Step 1: Mechanical intake
                success = self.hardware.feed_card()
                if not success:
                    logger.error("Mechanical feed error. Pausing system for safety.")
                    self.state.log_failed_scan()
                    continue

                # Step 2: Grab visual optical data
                frame = self.camera.get_frame()
                if frame is None:
                    logger.warning("Blank frame received from optical view.")
                    self.state.log_failed_scan()
                    continue

                # Step 3: Match image data against database (Simulated for now)
                current_card = self._process_and_identify_card(frame)
                if current_card is None:
                    self.state.log_failed_scan()
                    continue

                # Step 4: Actuate sorting gates based on Model logic
                target_bin = current_card.get_target_bin()
                self.hardware.sort_to_bin(target_bin)

                # Step 5: Update the central system state model
                self.state.log_successful_sort(current_card)

                # Mechanical settling delay between cards
                time.sleep(1.5)

        except KeyboardInterrupt:
            logger.warning("Sorting process interrupted by user command.")
        finally:
            self.stop_sorting()

    def stop_sorting(self):
        """Clean shutdown of all active view streams and session logs."""
        if not self.is_active:
            return

        self.is_active = False
        self.camera.close()
        self.state.stop_session()

        # Print a short final diagnostic report generated by the Model
        report = self.state.get_session_report()
        logger.info(f"📋 Session Statistics: {report}")
        logger.info("🎮 SorterController terminated safely.")
