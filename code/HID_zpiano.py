# ukulele_matrix_hid_comma_combo_L.py
import time
import board
import digitalio
import neopixel
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# --- HID setup ---
keyboard = Keyboard(usb_hid.devices)

# --- NeoPixel setup ---
PIXEL_PIN = board.D0
NUM_PIXELS = 9
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=0.2, auto_write=False)

# --- Matrix setup ---
ROW_PINS = [board.D1, board.D2, board.D3]
COL_PINS = [board.D4, board.D5, board.D6]

rows = [digitalio.DigitalInOut(rp) for rp in ROW_PINS]
cols = [digitalio.DigitalInOut(cp) for cp in COL_PINS]

for r in rows:
    r.direction = digitalio.Direction.OUTPUT
    r.value = True  # inactive

for c in cols:
    c.direction = digitalio.Direction.INPUT
    c.pull = digitalio.Pull.UP

# --- Key mappings ---
# 1–7 normal keys
normal_keys = [Keycode.Z, Keycode.X, Keycode.C,
               Keycode.V, Keycode.B, Keycode.N, Keycode.M]

# 8th key: comma normally
COMMA_INDEX = 7  # key 8
# 9th key: combo key
COMBO_INDEX = 8

key_states = [False] * 9
last_change_time = [0.0] * 9
DEBOUNCE_MS = 20

# --- LED feedback ---
def flash(idx, color=(0, 80, 255)):
    pixels.fill((0, 0, 0))
    if 0 <= idx < NUM_PIXELS:
        pixels[idx] = color
    pixels.show()

# --- Handle key events ---
def handle_key_event(idx, pressed):
    combo_held = key_states[COMBO_INDEX]

    # Combo key itself
    if idx == COMBO_INDEX:
        key_states[idx] = pressed
        flash(idx, (255, 100, 0) if pressed else (0, 0, 0))
        return

    # Regular playable keys 1–7
    if idx < 7:
        key_states[idx] = pressed
        if pressed:
            keyboard.press(normal_keys[idx])
            flash(idx, (0, 80, 255))
        else:
            keyboard.release(normal_keys[idx])
            flash(idx, (0, 0, 0))
        return

    # 8th key: comma normally, 'L' with combo held
    if idx == COMMA_INDEX:
        key_states[idx] = pressed
        keycode = Keycode.L if combo_held else Keycode.COMMA
        if pressed:
            keyboard.press(keycode)
            flash(idx, (0, 255, 255))  # cyan
        else:
            keyboard.release(keycode)
            flash(idx, (0, 0, 0))
        return

# --- Matrix scanning ---
def scan_matrix():
    now = time.monotonic() * 1000.0
    for r_i, r in enumerate(rows):
        # drive row low
        for rr in rows:
            rr.value = True
        r.value = False
        time.sleep(0.002)

        for c_i, c in enumerate(cols):
            idx = r_i * 3 + c_i
            if idx >= len(key_states):
                continue
            pressed = not c.value

            # Debounce
            if pressed != key_states[idx] and (now - last_change_time[idx]) > DEBOUNCE_MS:
                last_change_time[idx] = now
                handle_key_event(idx, pressed)

        time.sleep(0.001)

# --- Main loop ---
print("HID keyboard ready: Z–M normal, combo (key 9)")

while True:
    scan_matrix()
    time.sleep(0.003)
