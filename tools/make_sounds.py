"""Synthesize simple cartoon sound effects as WAV files (no external assets needed).

Outputs to assets/sfx/. The app plays these via QSoundEffect.
"""
import math
import os
import random
import struct
import wave

SR = 44100
OUT = r"C:\git-repo\pet\assets\sfx"


def save(name, samples):
    os.makedirs(OUT, exist_ok=True)
    frames = b"".join(struct.pack("<h", max(-32767, min(32767, int(s * 32767)))) for s in samples)
    with wave.open(os.path.join(OUT, name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(frames)
    print(name, len(samples) / SR, "s")


def env(n, attack=0.02, decay=0.2):
    a = int(attack * SR)
    out = []
    for i in range(n):
        if i < a:
            out.append(i / max(1, a))
        else:
            out.append(math.exp(-(i - a) / (decay * SR)))
    return out


def lowpass_noise(n, cutoff=0.2, amp=1.0):
    last = 0.0
    out = []
    for _ in range(n):
        x = random.uniform(-1, 1)
        last += cutoff * (x - last)
        out.append(last * amp)
    return out


def roar():
    n = int(0.95 * SR)
    noise = lowpass_noise(n, 0.12, 0.6)
    e = env(n, 0.03, 0.35)
    out = []
    for i in range(n):
        t = i / SR
        f = 85 + 35 * math.sin(2 * math.pi * 6 * t)  # wobbling pitch
        saw = 2 * ((f * t) % 1) - 1
        wob = 0.7 + 0.3 * math.sin(2 * math.pi * 9 * t)
        out.append((0.55 * saw + noise[i]) * e[i] * wob * 0.8)
    save("tap1_roar.wav", out)


def lunge():
    n = int(0.7 * SR)
    out = [0.0] * n
    # whoosh: noise swell in first 0.45s
    wn = int(0.45 * SR)
    whoosh = lowpass_noise(wn, 0.35, 0.5)
    for i in range(wn):
        out[i] += whoosh[i] * math.sin(math.pi * i / wn) * 0.7
    # snap at ~0.45s
    s0 = int(0.45 * SR)
    snap = lowpass_noise(int(0.08 * SR), 0.8, 1.0)
    e = env(len(snap), 0.002, 0.02)
    for i, s in enumerate(snap):
        if s0 + i < n:
            out[s0 + i] += s * e[i] * 0.9
    save("tap2_lunge.wav", out)


def yawn():
    n = int(0.8 * SR)
    e = env(n, 0.05, 0.4)
    out = []
    for i in range(n):
        t = i / SR
        f = 320 - 160 * (t / 0.8)
        out.append(math.sin(2 * math.pi * f * t) * e[i] * 0.5)
    save("tap3_yawn.wav", out)


def boing():
    n = int(0.45 * SR)
    e = env(n, 0.005, 0.2)
    out = []
    for i in range(n):
        t = i / SR
        f = 420 * math.exp(-6 * t) + 90
        tri = 2 / math.pi * math.asin(math.sin(2 * math.pi * f * t))
        out.append(tri * e[i] * 0.55)
    save("drag_boing.wav", out)


def click():
    n = int(0.1 * SR)
    e = env(n, 0.003, 0.03)
    out = []
    for i in range(n):
        t = i / SR
        out.append(math.sin(2 * math.pi * 520 * t) * e[i] * 0.4)
    save("click.wav", out)


if __name__ == "__main__":
    random.seed(7)
    roar()
    lunge()
    yawn()
    boing()
    click()
