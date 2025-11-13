import time
import board
import digitalio
import touchio
import neopixel
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.control_change import ControlChange

### MIDI setup ###
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)

### Pin setup ###
ROW_PINS = [board.D1, board.D2, board.D3]
COL_PINS = [board.D4, board.D5, board.D6]
TOUCH_PINS = [board.D7, board.D8, board.D9, board.D10]
PIXEL_PIN = board.D0
NUM_PIXELS = 9

pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=0.3, auto_write=False)

### Matrix setup ###
rows = []
cols = []

for rp in ROW_PINS:
    r = digitalio.DigitalInOut(rp)
    r.direction = digitalio.Direction.OUTPUT
    r.value = True
    rows.append(r)

for cp in COL_PINS:
    c = digitalio.DigitalInOut(cp)
    c.direction = digitalio.Direction.INPUT
    c.pull = digitalio.Pull.UP
    cols.append(c)

### Touch setup ###
touchpads = [touchio.TouchIn(p) for p in TOUCH_PINS]
touch_baselines = [t.raw_value for t in touchpads]
touch_thresholds = [b + 150 for b in touch_baselines]
touch_states = [False] * 4

### Key note layout ###
BASE_NOTE = 48  # C3
note_numbers = [BASE_NOTE + i for i in range(9)]  # C3 to D4
key_states = [False] * 9

### CC map (GarageBand compatible) ###
cc_map = [1, 74, 7, 91]  # Mod, Filter, Volume, Reverb

### Colors ###
COLOR_NOTE = (0, 180, 255)
COLOR_TOUCH = [(255, 100, 0), (0, 255, 80), (255, 255, 0), (150, 0, 255)]
COLOR_OFF = (0, 0, 0)

def update_pixels():
    pixels.fill(COLOR_OFF)
    for i, pressed in enumerate(key_states):
        if pressed:
            pixels[i] = COLOR_NOTE
    pixels.show()

def flash_pixel(i, color, duration=0.08):
    pixels[i] = color
    pixels.show()
    time.sleep(duration)
    pixels[i] = COLOR_OFF
    pixels.show()

def scan_keys():
    for r_i, r in enumerate(rows):
        r.value = False
        for c_i, c in enumerate(cols):
            idx = r_i * 3 + c_i
            pressed = not c.value
            if pressed and not key_states[idx]:
                note = note_numbers[idx]
                midi.send(NoteOn(note, 100))
                flash_pixel(idx, COLOR_NOTE)
            elif not pressed and key_states[idx]:
                note = note_numbers[idx]
                midi.send(NoteOff(note, 0))
            key_states[idx] = pressed
        r.value = True

def scan_touches():
    for i, t in enumerate(touchpads):
        raw = t.raw_value
        value = min(max(int((raw - touch_baselines[i]) / 8), 0), 127)
        touched = raw > touch_thresholds[i]

        if touched:
            midi.send(ControlChange(cc_map[i], value))
            pixels.fill(COLOR_TOUCH[i])
            pixels.show()
        elif touch_states[i]:
            midi.send(ControlChange(cc_map[i], 0))
            update_pixels()
        touch_states[i] = touched

print("🎹 GarageBand MIDI Pad ready — plug in and play!")

while True:
    scan_keys()
    scan_touches()
    time.sleep(0.01)
