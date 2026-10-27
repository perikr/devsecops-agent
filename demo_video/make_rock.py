#!/usr/bin/env python3
"""Synthesize an original 4-bar rock loop (drums, bass, distorted power chords) as WAV. Stdlib only."""
import array, math, random, struct, sys, wave

SR, BPM = 44100, 150
BEAT = 60 / BPM
ROOTS = [110.0, 87.31, 130.81, 98.0]  # Am F C G, one bar each
random.seed(7)


def saw(f, t):
    return 2 * ((f * t) % 1.0) - 1


def render():
    n = int(SR * BEAT * 4 * len(ROOTS))
    out = array.array("f", [0.0]) * n
    def add(start, sig):
        s = int(start * SR)
        for i, v in enumerate(sig):
            if s + i >= n: break
            out[s + i] += v
    def kick():
        return [math.sin(2 * math.pi * (45 * t + 75 * (1 - math.exp(-t * 25)) / 25 * 0 + 75 * (1 - math.exp(-t * 30)) / 30)) * math.exp(-t * 14) * 1.1 for t in (i / SR for i in range(int(SR * .3)))]
    def snare():
        return [(random.uniform(-1, 1) * .8 + math.sin(2 * math.pi * 190 * t) * .5) * math.exp(-t * 22) for t in (i / SR for i in range(int(SR * .22)))]
    def hat():
        prev = 0.0
        res = []
        for i in range(int(SR * .06)):
            x = random.uniform(-1, 1); res.append((x - prev) * .35 * math.exp(-i / SR * 70)); prev = x
        return res
    K, S, H = kick(), snare(), hat()
    for bar, root in enumerate(ROOTS):
        b0 = bar * 4 * BEAT
        for beat in range(4):
            if beat in (0, 2): add(b0 + beat * BEAT, K)
            if beat in (1, 3): add(b0 + beat * BEAT, S)
        add(b0 + 2.5 * BEAT, K)
        for e in range(8): add(b0 + e * BEAT / 2, H)
        for e in range(8):  # palm-muted eighth-note power chords + bass
            t0 = b0 + e * BEAT / 2
            L = int(SR * BEAT / 2 * (0.55 if e % 4 != 3 else 0.9))
            g, b = [], []
            for i in range(L):
                t = i / SR; env = math.exp(-t * 7)
                chord = sum(saw(f, t + k * .0007) for f in (root * 2, root * 3, root * 4) for k in (0, 1)) / 6
                g.append(math.tanh(chord * 7) * .33 * env)
                b.append(saw(root / 2 * 2, t) * .4 * math.exp(-t * 5))
            add(t0, [x + y for x, y in zip(g, b)])
    peak = max(abs(x) for x in out) or 1
    return [x / peak * .85 for x in out]


if __name__ == "__main__":
    data = render()
    with wave.open(sys.argv[1], "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(x * 32767)) for x in data))
    print("wrote", sys.argv[1], f"{len(data) / SR:.1f}s loop")
