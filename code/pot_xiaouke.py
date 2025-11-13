import board
import digitalio
import touchio
import analogio
import time

import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

# ---------------------------
# Pin mapping
# ---------------------------
ROW_PINS = [board.D1, board.D2, board.D3]       # 3 rows of matrix
COL_PINS = [board.D4, board.D5, board.D6]       # 3 columns of matrix
TOUCH_PINS = [board.D7, board.D8, board.D9, board.D10]  # 4 strings
POT_PIN = board.A0                                # potentiometer

# ---------------------------
# MIDI setup
# ---------------------------
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)
MIDI_ROOTS = [60, 62, 64, 65, 67, 69, 71]  # C D E F G A B

# ---------------------------
# State variables
# ---------------------------
minor_pressed = False
seventh_pressed = False
key_states = [False] * 9
last_touch_vals = [False] * 4
active_notes = set()

# ---------------------------
# Matrix setup
# ---------------------------
rows = [digitalio.DigitalInOut(p) for p in ROW_PINS]
for r in rows:
    r.direction = digitalio.Direction.INPUT

cols = [digitalio.DigitalInOut(p) for p in COL_PINS]
for c in cols:
    c.direction = digitalio.Direction.INPUT
    c.pull = digitalio.Pull.UP

NUM_ROWS = len(rows)
NUM_COLS = len(cols)
DEBOUNCE_MS = 20
state = [[0]*NUM_COLS for _ in range(NUM_ROWS)]
last_change_ts = [[0]*NUM_COLS for _ in range(NUM_ROWS)]

# ---------------------------
# Touch setup
# ---------------------------
touches = [touchio.TouchIn(p) for p in TOUCH_PINS]
last_touch_vals = [False] * len(touches)

# ---------------------------
# Potentiometer setup
# ---------------------------
pot = analogio.AnalogIn(POT_PIN)
MAX_SLIDE = 12  # max semitones up

# ---------------------------
# Helper functions
# ---------------------------
def set_row_active(idx):
    for r in rows:
        r.direction = digitalio.Direction.INPUT
    rows[idx].direction = digitalio.Direction.OUTPUT
    rows[idx].value = False

def release_rows():
    for r in rows:
        r.direction = digitalio.Direction.INPUT

def handle_key_event(r, c, pressed):
    global minor_pressed, seventh_pressed
    idx = r * NUM_COLS + c
    key_states[idx] = pressed
    if idx == 7:
        minor_pressed = pressed
    elif idx == 8:
        seventh_pressed = pressed

def get_chord_notes(root_note):
    """Return 4 notes for GCEA strings with modifiers."""
    fifth = root_note + 7
    octave = root_note + 12
    major_third = root_note + 4
    minor_third = root_note + 3
    minor7 = root_note + 10

    if minor_pressed and seventh_pressed:  # Minor7
        return [fifth, root_note, minor_third, minor7]
    elif minor_pressed:  # Minor
        return [fifth, root_note, minor_third, octave]
    elif seventh_pressed:  # Dominant7
        return [fifth, root_note, major_third, minor7]
    else:  # Major
        return [fifth, root_note, major_third, octave]

def get_slide_offset():
    """Map potentiometer reading to slide semitone offset (0 to MAX_SLIDE)."""
    return int((pot.value / 65535) * MAX_SLIDE)

def handle_touch_event(i, on):
    if on:
        active_chords = [idx for idx in range(7) if key_states[idx]]
        if active_chords:
            root_idx = active_chords[0]
            root_note = MIDI_ROOTS[root_idx]
            chord_notes = get_chord_notes(root_note)
            if i < len(chord_notes):
                slide = get_slide_offset()
                note = chord_notes[i] + slide
                midi.send(NoteOn(note, 100))
                time.sleep(0.05)  # short pluck duration
                midi.send(NoteOff(note, 0))

def scan_matrix():
    now = time.monotonic_ns() // 1_000_000
    for r in range(NUM_ROWS):
        set_row_active(r)
        time.sleep(0.00025)
        for c in range(NUM_COLS):
            pressed = not cols[c].value
            if pressed != (state[r][c] == 1):
                if last_change_ts[r][c] == 0:
                    last_change_ts[r][c] = now
                elif (now - last_change_ts[r][c]) >= DEBOUNCE_MS:
                    state[r][c] = 1 if pressed else 0
                    handle_key_event(r, c, pressed)
                    last_change_ts[r][c] = 0
            else:
                last_change_ts[r][c] = 0
    release_rows()

def poll_touches():
    for i, t in enumerate(touches):
        val = bool(t.value)
        if val != last_touch_vals[i]:
            last_touch_vals[i] = val
            last_touch_vals[i] = val
            handle_touch_event(i, val)

# ---------------------------
# Main loop
# ---------------------------
print("🎸 Ukulele Controller — sliding chords with potentiometer")
while True:
    scan_matrix()
    poll_touches()
    time.sleep(0.01)
