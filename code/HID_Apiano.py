import time
import board
import digitalio
import touchio
import neopixel
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# --- HID Setup ---
keyboard = Keyboard(usb_hid.devices)

# --- NeoPixel Setup ---
PIXEL_PIN = board.D0
NUM_PIXELS = 9
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=0.2, auto_write=False)

# --- Matrix Pins ---
ROW_PINS = [board.D1, board.D2, board.D3]
COL_PINS = [board.D4, board.D5, board.D6]

rows = [digitalio.DigitalInOut(rp) for rp in ROW_PINS]
cols = [digitalio.DigitalInOut(cp) for cp in COL_PINS]

for r in rows:
    r.direction = digitalio.Direction.OUTPUT
    r.value = True

for c in cols:
    c.direction = digitalio.Direction.INPUT
    c.pull = digitalio.Pull.UP

# --- Capacitive Touch Pads ---
touch_octave_down = touchio.TouchIn(board.D7)  # sends Z
touch_octave_up = touchio.TouchIn(board.D8)    # sends X
touch_combo = touchio.TouchIn(board.D9)        # combo key
touch_unused = touchio.TouchIn(board.D10)      # optional

# --- Key Mappings ---
normal_keys = [
    Keycode.A, Keycode.S, Keycode.D,
    Keycode.F, Keycode.G, Keycode.H,
    Keycode.J, Keycode.K, Keycode.L
]

# Combo mapping (touchpad 4 held)
combo_map = {
    0: Keycode.W,  # A
    1: Keycode.E,  # S
    3: Keycode.T,  # F
    4: Keycode.Y,  # G
    5: Keycode.U,  # H
    7: Keycode.O,  # K
    8: Keycode.P   # L
}

# --- State Tracking ---
key_states = [False] * 9
last_change_time = [0.0] * 9
DEBOUNCE_MS = 20

octave_states = [False, False]  # [down, up]
combo_state = False

# --- LED Feedback ---
def flash(idx, color=(0, 80, 255)):
    pixels.fill((0, 0, 0))
    if 0 <= idx < NUM_PIXELS:
        pixels[idx] = color
    pixels.show()

# --- Handle Key Events ---
def handle_key_event(idx, pressed):
    global combo_state

    if pressed:
        # Determine if combo is active for this key
        keycode = combo_map.get(idx, normal_keys[idx]) if combo_state else normal_keys[idx]
        keyboard.press(keycode)
        # LED color
        color = (0, 255, 0) if combo_state else (0, 80, 255)
        flash(idx, color)
    else:
        # Release key
        keycode = combo_map.get(idx, normal_keys[idx]) if combo_state else normal_keys[idx]
        keyboard.release(keycode)
        flash(idx, (0, 0, 0))

# --- Scan Matrix ---
def scan_matrix():
    now = time.monotonic() * 1000.0
    for r_i, r in enumerate(rows):
        # drive current row low
        for rr in rows:
            rr.value = True
        r.value = False
        time.sleep(0.002)

        for c_i, c in enumerate(cols):
            idx = r_i * 3 + c_i
            if idx >= len(key_states):
                continue
            pressed = not c.value

            if pressed != key_states[idx] and (now - last_change_time[idx]) > DEBOUNCE_MS:
                last_change_time[idx] = now
                key_states[idx] = pressed
                handle_key_event(idx, pressed)

        time.sleep(0.001)

# --- Main Loop ---
print("HID keyboard ready: 9-key matrix A-L, combo with touchpad 4, octave Z/X on touchpad 1/2")

while True:
    # Octave pads
    if touch_octave_down.value and not octave_states[0]:
        keyboard.press(Keycode.Z)
        octave_states[0] = True
    elif not touch_octave_down.value and octave_states[0]:
        keyboard.release(Keycode.Z)
        octave_states[0] = False

    if touch_octave_up.value and not octave_states[1]:
        keyboard.press(Keycode.X)
        octave_states[1] = True
    elif not touch_octave_up.value and octave_states[1]:
        keyboard.release(Keycode.X)
        octave_states[1] = False

    # Combo pad
    combo_state = touch_combo.value

    # Scan key matrix
    scan_matrix()
    time.sleep(0.003)
