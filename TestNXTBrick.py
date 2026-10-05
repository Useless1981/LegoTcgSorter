import time
import nxt.locator
# Import the modern Port enum instead of old global constants
from nxt.motor import Port


def test_nxt_hardware():
    print("==================================================")
    print("NXT 2.0 TCG Sorter - Hardware-Verbindungstest")
    print("==================================================")
    # NXT-Brick need to be connected and turned on. A motor must be connected on port a.
    try:
        print("Suche NXT-Brick via USB/Bluetooth...")

        # Open the connection cleanly using the context manager
        with nxt.locator.find() as brick:

            # Read device metadata from the connected brick
            device_info = brick.get_device_info()
            print(f"✅ Verbindung erfolgreich!")
            print(f"   Name des Bricks: {device_info if isinstance(device_info, tuple) else device_info}")
            print(f"   Batteriestatus:  {brick.get_battery_level() / 1000:.2f} V")
            print("--------------------------------------------------")

            # Initialize the motor object assigned to Port A using the brick factory method
            motor_a = brick.get_motor(Port.A)

            # Test sequence: Rotate motor forward (e.g., pulling in a card)
            print("▶️ Starte Motor-Testsequenz...")
            print("Drehe Motor A um 360 Grad vorwärts (Speed: 60)...")

            # Fix: In nxt-python 3, use positional arguments for turn()
            # Syntax: turn(power, tacho_units)
            motor_a.turn(60, 360)

            # Short delay to let the motor finish its rotation and settle down
            time.sleep(2)

            # Test sequence: Rotate motor backward (e.g., clearing a jam)
            print("↩️ Drehe Motor A um 360 Grad rückwärts (Speed: -60)...")
            # To reverse, we use negative power
            motor_a.turn(-60, 360)

            # Wait for the backward rotation to finish
            time.sleep(2)

            print("--------------------------------------------------")
            print("🎉 Test erfolgreich abgeschlossen! Die Hardware reagiert.")

    except nxt.locator.BrickNotFoundError:
        print("\n❌ FEHLER: Der NXT-Brick wurde nicht gefunden!")
        print("Bitte prüfen:")
        print("1. Ist der Brick eingeschaltet?")
        print("2. Ist das USB-Kabel fest eingesteckt?")
        print("3. Wurde der Zadig-Treiber (libusb-win32) korrekt aufgespielt?")

    except Exception as e:
        print(f"\n❌ Ein unerwarteter Fehler ist aufgetreten: {e}")

    print("==================================================")


if __name__ == "__main__":
    test_nxt_hardware()
