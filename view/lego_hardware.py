import time
import nxt.locator
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
        self.feeder_motor = self.brick.get_motor(Port.A)
        self.sorter_motor = self.brick.get_motor(Port.B)

        print("🤖 LegoHardware View: Initialized motor mappings on Port A and B.")

    def feed_card(self) -> bool:
        """
        Actuates the intake mechanism to pull exactly one card under the camera.
        :return: True if mechanical step completed successfully
        """
        print("🤖 LegoHardware: Actuating feeder motor to draw a card...")
        try:
            # Example: Turn motor A forward by 360 degrees to activate friction wheel
            self.feeder_motor.turn(60, 360)
            time.sleep(0.5)  # Let the mechanism settle down
            return True
        except Exception as e:
            print(f"❌ LegoHardware Error (feeder): {e}")
            return False

    def sort_to_bin(self, bin_number: int) -> bool:
        """
        Moves the mechanical sorting gate or carousel to route the card to a specific bin.
        :param bin_number: Target bin identifier calculated by the model
        :return: True if sorting gate moved successfully
        """
        print(f"🤖 LegoHardware: Adjusting mechanism for target bin {bin_number}...")
        try:
            # TODO: Implement your sorting logic here (e.g., branching or carousel rotation)
            # Example placeholder: turn sorter motor based on bin multiplier
            degrees = bin_number * 90
            if degrees > 0:
                self.sorter_motor.turn(50, degrees)
            return True
        except Exception as e:
            print(f"❌ LegoHardware Error (sorter): {e}")
            return False
