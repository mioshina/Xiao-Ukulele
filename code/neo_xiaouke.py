# ukulele_midi_7led_fast.py
# CircuitPython ukulele controller — fast touch response
# 3×3 matrix, 4 capacitive strings, 7-LED NeoPixel strip
# Hardware:
# Rows: D1-D3
# Cols: D4-D6
# NeoPixel strip: D0 (7 LEDs)
# Touch pads (G,C,E,A): D7-D10
# Requires adafruit_midi and neopixel libraries

import board, digitalio, touchio, neopixel, time
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

# ---------------- Pins ----------------
ROW_PINS = [board.D1, board.D2, board.D3]
COL_PINS = [board.D4, board.D5, board.D6]
TOUCH_PINS = [board.D7, board.D8, board.D9, board.D10]
PIXEL_PIN = board.D0
NUM_LEDS = 7

pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_LEDS, brightness=0.4, auto_write=False)

# ---------------- MIDI ----------------
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)
MIDI_ROOTS = [60, 62, 64, 65, 67, 69, 71]  # C D E F G A B (change this for octave)

# ---------------- Colors ----------------
COLOR_MAJOR  = (255, 100, 180)
COLOR_MINOR  = (255, 255, 0)
COLOR_7TH    = (0, 100, 255)
COLOR_MINOR7 = (100, 255, 255)
COLOR_OFF    = (0, 0, 0)
COLOR_NEUTRAL= (80, 80, 80)

# ---------------- States ----------------
minor_pressed = False
seventh_pressed = False
key_states = [False] * 9
last_touch_vals = [False] * 4
shimmer_queue = []  # for non-blocking shimmer

# ---------------- Matrix setup ----------------
rows = [digitalio.DigitalInOut(p) for p in ROW_PINS]
for r in rows: r.direction = digitalio.Direction.INPUT

cols = [digitalio.DigitalInOut(p) for p in COL_PINS]
for c in cols:
    c.direction = digitalio.Direction.INPUT
    c.pull = digitalio.Pull.UP

NUM_ROWS = len(rows)
NUM_COLS = len(cols)
DEBOUNCE_MS = 20
state = [[0]*NUM_COLS for _ in range(NUM_ROWS)]
last_change_ts = [[0]*NUM_COLS for _ in range(NUM_ROWS)]

# ---------------- Touch setup ----------------
touches = [touchio.TouchIn(p) for p in TOUCH_PINS]
for t in touches:
    t.threshold = 1200  # faster, more sensitive response

# ---------------- Helpers ----------------
def set_row_active(i):
    for r in rows: r.direction = digitalio.Direction.INPUT
    rows[i].direction = digitalio.Direction.OUTPUT
    rows[i].value = False

def release_rows():
    for r in rows: r.direction = digitalio.Direction.INPUT

def chord_color():
    if minor_pressed and seventh_pressed: return COLOR_MINOR7
    if minor_pressed: return COLOR_MINOR
    if seventh_pressed: return COLOR_7TH
    return COLOR_MAJOR

def update_leds():
    color = chord_color()
    for i in range(7):
        pixels[i] = color if key_states[i] else COLOR_OFF
    pixels.show()

def add_shimmer(color, steps=5):
    """Add shimmer to queue (non-blocking)"""
    shimmer_queue.append({'color': color, 'step': 1, 'steps': steps})

def process_shimmer():
    """Non-blocking shimmer update"""
    if not shimmer_queue: return
    finished = []
    for s in shimmer_queue:
        step = s['step']
        steps = s['steps']
        c = s['color']
        r,g,b = tuple(int(v*step/steps) for v in c)
        pixels.fill((r,g,b))
        pixels.show()
        s['step'] +=1
        if s['step'] > steps:
            finished.append(s)
    for f in finished: shimmer_queue.remove(f)
    # After shimmer, restore normal LED state
    if not shimmer_queue:
        update_leds()

def handle_key_event(r, c, pressed):
    global minor_pressed, seventh_pressed
    idx = r*NUM_COLS + c
    key_states[idx] = pressed
    if idx == 7: minor_pressed = pressed
    elif idx == 8: seventh_pressed = pressed
    update_leds()

def get_chord_notes(root):
    fifth = root + 7
    octave = root + 12
    maj3 = root + 4
    min3 = root + 3
    min7 = root + 10
    if minor_pressed and seventh_pressed: return [fifth, root, min3, min7]
    if minor_pressed: return [fifth, root, min3, octave]
    if seventh_pressed: return [fifth, root, maj3, min7]
    return [fifth, root, maj3, octave]

def handle_touch_event(i, on):
    if not on: return
    active = [k for k in range(7) if key_states[k]]
    if not active:
        pixels.fill(COLOR_NEUTRAL)
        pixels.show()
        time.sleep(0.06)
        update_leds()
        return
    root_note = MIDI_ROOTS[active[0]]
    chord_notes = get_chord_notes(root_note)
    note = chord_notes[i]
    midi.send(NoteOn(note, 100))
    add_shimmer(chord_color())
    time.sleep(0.01)
    midi.send(NoteOff(note, 0))

def scan_matrix():
    now = time.monotonic_ns()//1_000_000
    for r in range(NUM_ROWS):
        set_row_active(r)
        time.sleep(0.0003)
        for c in range(NUM_COLS):
            pressed = not cols[c].value
            if pressed != (state[r][c]==1):
                if last_change_ts[r][c]==0:
                    last_change_ts[r][c]=now
                elif (now-last_change_ts[r][c])>=DEBOUNCE_MS:
                    state[r][c]=1 if pressed else 0
                    handle_key_event(r,c,pressed)
                    last_change_ts[r][c]=0
            else:
                last_change_ts[r][c]=0
    release_rows()

def poll_touches():
    for i,t in enumerate(touches):
        v = bool(t.value)
        if v != last_touch_vals[i]:
            last_touch_vals[i] = v
            handle_touch_event(i, v)

# ---------------- Main ----------------
print("🎸 Ukulele MIDI controller — fast touch & 7-LED ready")
update_leds()

while True:
    scan_matrix()
    poll_touches()
    process_shimmer()  # non-blocking LED animation
    time.sleep(0.002)  # faster polling for touch responsiveness
