import logging
from model.card import Card

# Grab the configured logger instance for this specific module
logger = logging.getLogger("TcgSorter.Model")


class SorterState:
    def __init__(self):
        self.is_calibrated: bool = False
        self.is_running: bool = False
        self.total_processed: int = 0
        self.failed_scans: int = 0
        self.bin_counts: dict[int, int] = {}
        self.card_log: list[Card] = []

    def start_session(self):
        self.is_running = True
        # ... reset counters ...
        logger.info("New sorting session started. All counters initialized.")

        # DIESE METHODE FEHLTE:

    def stop_session(self):
        """Stops the active session."""
        self.is_running = False
        logger.info(f"Sorting session stopped. Total cards sorted: {self.total_processed}")

    def get_session_report(self) -> dict:
        """
        Generates a summary data dictionary. Useful for view components/GUIs.
        """
        total = self.total_processed + self.failed_scans
        efficiency = (self.total_processed / total) * 100 if total > 0 else 100.0

        return {
            "total_processed": self.total_processed,
            "failed_scans": self.failed_scans,
            "bin_distribution": self.bin_counts.copy(),
            "efficiency_rate": efficiency
        }

    def log_successful_sort(self, card: Card):
        self.total_processed += 1
        self.card_log.append(card)
        target_bin = card.get_target_bin()
        self.bin_counts[target_bin] = self.bin_counts.get(target_bin, 0) + 1

        # Using debug for verbose data and info for general tracking
        logger.debug(f"Card details: Name={card.get_name()}, ID={card.get_id()}")
        logger.info(f"Successfully sorted card '{card.get_name()}' into bin {target_bin}.")

    def log_failed_scan(self):
        self.failed_scans += 1
        logger.warning(f"Failed to identify card! Total system anomalies: {self.failed_scans}")
