import sys
import logging
import nxt.locator
from logger_config import setup_logger
from controller.sorter_controller import SorterController


def main():
    # 1. Boot up the centralized logging infrastructure
    logger = setup_logger()
    logger.info("🚀 Launching LEGO Mindstorms TCG Sorter Software Pipeline...")

    try:
        # 2. Establish connection to the hardware brick interface
        logger.info("Connecting to physical NXT 2.0 Brick via USB...")

        with nxt.locator.find() as brick:
            logger.info("NXT Brick connected. Syncing hardware abstraction layers...")

            # 3. Instantiate the MVC framework via the controller
            controller = SorterController(brick)

            # 4. Trigger the main loop (Run a test batch of 4 cards)
            controller.start_sorting(max_cards=4)

    except nxt.locator.BrickNotFoundError:
        logger.critical("Execution Halted: No NXT brick detected. Verify USB cables and Zadig drivers.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Fatal System Exception: {e}", exc_info=True)
        sys.exit(1)

    logger.info("🚀 System shut down cleanly. Goodbye.")


if __name__ == "__main__":
    main()
