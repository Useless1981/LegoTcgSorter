import time
import nxt.locator
from numpy.f2py.auxfuncs import throw_error
from nxt.motor import Port


class LegoHardware:
    """
    View component managing the physical LEGO Mindstorms NXT 2.0 hardware.
    Handles motor actuation and raw physical movements.
    """

    def __init__(self, brick):
        """
        Initializes the hardware view with an active NXT brick connection.
        :param brick: The active nxt.brick.Brick object provided by the controller
        """
        self.brick = brick
        # Initialize motors using the modern factory method
        self.stack_feeder_motor = self.brick.get_motor(Port.A)
        self.sorter_motor = self.brick.get_motor(Port.B)
        self.bin_feeder_motor = self.brick.get_motor(Port.C)
        self.sorter_gear_ratio: float = 60/20
        self.bin_angle: int = 60

        print("🤖 LegoHardware View: Initialized motor mappings on Port A and B.")

    def feed_card(self) -> bool:
        """
        Actuates the intake mechanism to pull exactly one card under the camera.
        :return: True if mechanical step completed successfully
        """
        print("🤖 LegoHardware: Actuating stck feeder motor to draw a card...")
        try:
            # Example: Turn motor A forward by 360 degrees to activate friction wheel
            self.stack_feeder_motor.turn(-60, 360)
            time.sleep(0.5)  # Let the mechanism settle down
            return True
        except Exception as e:
            print(f"❌ LegoHardware Error (stack feeder): {e}")
            return False

    def sort_to_bin(self, bin_number: int) -> bool:
        """
        Moves the mechanical sorting gate or carousel to route the card to a specific bin.
        :param bin_number: Target bin identifier calculated by the model
        :return: True if sorting gate moved successfully
        """
        print(f"🤖 LegoHardware: Adjusting sorting table for target bin {bin_number}...")
        try:
            # TODO: Implement your sorting logic here (e.g., branching or carousel rotation)
            # Example placeholder: turn sorter motor based on bin multiplier
            degrees = bin_number * self.bin_angle * self.sorter_gear_ratio
            if not degrees > 0:
                print(f"❌ LegoHardware Error (sorter): Can not turn {degrees} degrees.")
                return False
            self.sorter_motor.turn(50, degrees)
            feed_to_bin: bool = self._feed_card_to_bin()
            if not feed_to_bin:
                print(f"❌ LegoHardware Error (sorter): Card not feed to bin.")
                return False
            reset: bool = self._reset_turntable(bin_number)
            if not reset:
                print(f"❌ LegoHardware Error (sorter): Table not resetted.")
                return False
            return True
        except Exception as e:
            print(f"❌ LegoHardware Error (sorter): {e}")
            return False

    def _reset_turntable(self, bin_number: int) -> bool:
        """
        Resets the sorter table for new card.
        :return: True if mechanical step completed successfully
        """
        print("🤖 LegoHardware: Actuating bin sorter motor to reset table...")
        try:
            bins_to_turn: int = 6 - bin_number
            degrees = bins_to_turn * self.bin_angle * self.sorter_gear_ratio
            if not degrees > 0:
                print(f"❌ LegoHardware Error (sorter reset): Can not turn {degrees} degrees.")
                return False
            self.sorter_motor.turn(50, degrees)
            return True
        except Exception as e:
            print(f"❌ LegoHardware Error (feeder reset): {e}")
            return False

    def _feed_card_to_bin(self):
        """
        Feeds a card from the sorter table to the bin.
        :return: True if mechanical step completed successfully
        """
        print("🤖 LegoHardware: Actuating bin feeder motor move card to bin...")
        try:
            # Example: Turn motor A forward by 360 degrees to activate friction wheel
            self.bin_feeder_motor.turn(60, 360)
            time.sleep(0.5)  # Let the mechanism settle down
            return True
        except Exception as e:
            print(f"❌ LegoHardware Error (bin feeder): {e}")
            return False