from time import sleep

from view.lego_hardware import LegoHardware
import nxt.locator


def main():
    with nxt.locator.find() as brick:
        lhw = LegoHardware(brick)
        lhw.feed_card()
        sleep(2)
        lhw.sort_to_bin(1)




if __name__ == "__main__":
    main()
