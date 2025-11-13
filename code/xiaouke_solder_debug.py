# ukulele_hardware_check_clean.py
# CircuitPython debug/test for ukulele PCB
# Checks matrix switches, capacitive pads, and NeoPixel strip

import board
import digitalio
import touchio
import neopixel
import time

# ---------------- Pins ----------------
ROW_PINS = [board.D1, board.D2, board.D3]
COL_PINS = [board.D4, board.D5, board.D6]
TOUCH_PINS = [board.D7, board.D8, board.D9, board.D10]
PIXEL_PIN = board.D0
NUM_LEDS = 7

# ---------------- Setup ----------------
rows = [digitalio.DigitalInOut(p) for p in ROW_PINS]
for r in rows:
    r.direction = digitalio.Direction.INPUT

cols = [digitalio.DigitalInOut(p) for p in COL_PINS]
for c in cols:
    c.direction = digitalio.Direction.INPUT
    c.pull = digitalio.Pull.UP

touches = [touchio.TouchIn(p) for p in TOUCH_PINS]
for t in touches:
    t.threshold = 1200

pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_LEDS, brightness=0.4, auto_write=True)

# ---------------- Matrix Helpers ----------------
def set_row_active(i):
    for r in rows:
        r.direction = digitalio.Direction.INPUT
    rows[i].direction = digitalio.Direction.OUTPUT
    rows[i].value = False

def release_rows():
    for r in rows:
        r.direction = digitalio.Direction.INPUT

# ---------------- LED Test ----------------
print("Testing NeoPixel strip...")
for i in range(NUM_LEDS):
    pixels.fill((0, 0, 0))
    pixels[i] = (255, 100, 0)
    print("LED", i + 1, "ON")
    time.sleep(0.2)
pixels.fill((0, 0, 0))
print("LED test complete\n")

# ---------------- Button + Touch Test ----------------
print("Testing matrix and touch inputs...\n")

while True:
    # Matrix keys
    for r in range(len(rows)):
        set_row_active(r)
        time.sleep(0.001)
        for c in range(len(cols)):
            if not cols[c].value:
                key_id = r * len(cols) + c
                print("Key", key_id + 1, "pressed (Row", r, "Col", c, ")")
                pixels.fill((0, 255, 0))
                pixels[key_id % NUM_LEDS] = (255, 0, 0)
                time.sleep(0.2)
                pixels.fill((0, 0, 0))
        release_rows()

    # Touch pads
    for i, t in enumerate(touches):
        if t.value:
            print("Touch Pad", i + 1, "active")
            pixels.fill((0, 0, 255))
            pixels[i % NUM_LEDS] = (255, 255, 255)
            time.sleep(0.2)
            pixels.fill((0, 0, 0))

    time.sleep(0.01)
