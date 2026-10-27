#!/usr/bin/env python3
"""Synthesize an original 16-bar corporate-tech loop (pad, plucked arpeggio, bass, soft beat) as WAV. Stdlib only.
Usage: make_music.py out.wav"""
import array, math, random, struct, sys, wave

SR, BPM = 44100, 108
BEAT = 60 / BPM
BAR = BEAT * 4
PAD = [[60, 64, 67], [59, 62, 67], [60, 64, 69], [60, 65, 69]]  # C G Am F voicings
BASS = [36, 43, 45, 41]
random.seed(11)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)


def env_pad(i, n):
    a, r = int(SR * .7), int(SR * .7)
    return min(1, i / a, (n - i) / r)


def pad_bar(notes):
    n = int(BAR * SR) + int(SR * .7)
    out, prev = [0.0] * n, 0.0
    for i in range(n):
        t = i / SR
        x = sum(((f * d * t) % 1.0) * 2 - 1 for m in notes for f in [hz(m)] for d in (.997, 1.0, 1.003)) / 9
        prev += .06 * (x - prev)  # one-pole low-pass: soft, warm
        out[i] = prev * 1.6 * max(0.0, env_pad(i, n))
    return out


def pluck(m):
    f, n = hz(m), int(SR * .45)
    return [(math.sin(2 * math.pi * f * t) + .3 * math.sin(4 * math.pi * f * t) + .12 * math.sin(6 * math.pi * f * t)) * math.exp(-t * 7) * min(1, t * 400)
            for t in (i / SR for i in range(n))]


def bass(m, beats):
    f, n = hz(m), int(SR * BEAT * beats)
    return [(math.sin(2 * math.pi * f * t) + .25 * math.sin(4 * math.pi * f * t)) * min(1, t * 200, (n - i) / (SR * .05)) * .9
            for i, t in ((i, i / SR) for i in range(n))]


def kick():
    return [math.sin(2 * math.pi * (48 * t + 60 * (1 - math.exp(-t * 28)) / 28)) * math.exp(-t * 11) for t in (i / SR for i in range(int(SR * .28)))]


def clap():
    return [random.uniform(-1, 1) * math.exp(-t * 26) for t in (i / SR for i in range(int(SR * .18)))]


def hat():
    prev, out = 0.0, []
    for i in range(int(SR * .05)):
        x = random.uniform(-1, 1); out.append((x - prev) * math.exp(-i / SR * 90)); prev = x
    return out


def render(bars=16):
    n = int((bars * BAR + 1.0) * SR)
    mix = array.array("f", [0.0]) * n
    def add(at, sig, g):
        s = int(at * SR)
        for i, v in enumerate(sig):
            if s + i < n: mix[s + i] += v * g
    pads = [pad_bar(c) for c in PAD]
    K, C, H = kick(), clap(), hat()
    cache = {}
    for b in range(bars):
        c, t0 = b % 4, b * BAR
        add(t0, pads[c], .30)
        notes = PAD[c] + [PAD[c][0] + 12]
        for e, idx in enumerate([0, 1, 2, 3, 2, 1, 2, 3]):
            m = notes[idx] + 12
            add(t0 + e * BEAT / 2, cache.setdefault(m, pluck(m)), .26 if e % 2 == 0 else .18)
        if b >= 2:
            add(t0, cache.setdefault(("b", BASS[c], 1.5), bass(BASS[c], 1.5)), .5)
            add(t0 + 2 * BEAT, cache.setdefault(("b2", BASS[c], 1), bass(BASS[c], 1)), .45)
        if b >= 4:
            for k in range(4): add(t0 + k * BEAT, K, .55)
            for e in range(1, 8, 2): add(t0 + e * BEAT / 2, H, .07)
        if b >= 8:
            for k in (1, 3): add(t0 + k * BEAT, C, .13)
    peak = max(abs(x) for x in mix) or 1
    return [x / peak * .85 for x in mix[: int(bars * BAR * SR)]]


if __name__ == "__main__":
    d = render()
    with wave.open(sys.argv[1], "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(x * 32767)) for x in d))
    print("wrote", sys.argv[1], f"{len(d) / SR:.1f}s loop")
