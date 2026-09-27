"""Synthesize crude placeholder SFX for No Brainers K3 (retail/build/defense/
breach/pickup). Only used for names Freesound could not source.

Writes 16-bit mono 44.1 kHz WAVs to PlaceholderAssets/Audio/, peak-normalized
to -1 dBFS. File names match the Unreal SoundWave names they import as.

Reuses helpers from synth_sfx.py (noise, sweep, groan, click, seq, env,
lowpass). Run a single name:
    python Tools/Audio/synth_k3.py <name>
Run all:
    python Tools/Audio/synth_k3.py
"""
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from synth_sfx import SR, t, env, noise, lowpass, sweep, rng  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "PlaceholderAssets", "Audio")

TARGET_PEAK_DB = -1.0


def write(name, x):
    peak = np.max(np.abs(x)) + 1e-9
    target = 10 ** (TARGET_PEAK_DB / 20.0)
    x = x / peak * target
    fade = min(len(x), int(SR * 0.01))
    if fade > 0:
        x[-fade:] *= np.linspace(1, 0, fade)
    data = (x * 32767).astype(np.int16)
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print("wrote", name, "{:.2f}s".format(len(x) / SR))


def click(f, dur=0.05, k=2, d=0.008):
    n = int(SR * dur)
    return lowpass(noise(dur), k) * env(n, 0.0005, d) + 0.4 * np.sin(2 * np.pi * f * t(dur)) * env(n, 0.0005, d)


def build_scan_beep():
    x = np.sin(2 * np.pi * 2500 * t(0.15)) * env(int(SR * 0.15), 0.002, 0.03)
    write("SFX_ScanBeep", x)


def build_cash_register():
    bell = sum(a * np.sin(2 * np.pi * f * t(0.9)) for f, a in [(1046, 1), (1568, 0.6), (2093, 0.3)])
    bell = bell * env(int(SR * 0.9), 0.002, 0.35)
    n = int(SR * 0.3)
    drawer = lowpass(noise(0.3), 3) * env(n, 0.01, 0.08)
    x = np.concatenate([bell, np.zeros(int(SR * 0.05))]) 
    x[int(SR * 0.55):int(SR * 0.55) + len(drawer)] += drawer[:len(x) - int(SR * 0.55)]
    write("SFX_CashRegister", x)


def build_socket_snap():
    n = int(SR * 0.3)
    thud = sweep(140, 45, 0.3) * env(n, 0.001, 0.08) + 0.5 * lowpass(noise(0.3), 20) * env(n, 0.001, 0.04)
    metal = click(3000, dur=0.08, k=1, d=0.02)
    x = np.zeros(int(SR * 0.45))
    x[:len(thud)] += thud
    i = int(SR * 0.12)
    x[i:i + len(metal)] += metal
    write("SFX_SocketSnap", x)


def build_repair():
    tap1 = click(1200, dur=0.06, k=3, d=0.015)
    tap2 = click(1400, dur=0.06, k=3, d=0.015)
    total = int(SR * 1.0)
    x = np.zeros(total)
    for i, seg in [(0.0, tap1), (0.35, tap2), (0.65, tap1)]:
        s = int(SR * i)
        x[s:s + len(seg)] += seg[:total - s]
    write("SFX_Repair", x)


def build_trap_zap():
    tt = t(0.6)
    buzz = np.sign(np.sin(2 * np.pi * 120 * tt)) * 0.6 + 0.4 * noise(0.6)
    x = lowpass(buzz, 2) * env(len(tt), 0.005, 0.15)
    write("SFX_TrapZap", x)


def build_trap_gas_hiss():
    x = (noise(0.9) - lowpass(noise(0.9), 6)) * env(int(SR * 0.9), 0.05, 0.35)
    write("SFX_TrapGasHiss", x)


def build_trap_spring_pop():
    tt = t(0.35)
    boing = sweep(900, 220, 0.35) * env(len(tt), 0.002, 0.1)
    stab = click(2600, dur=0.05, k=1, d=0.01)
    x = np.zeros(int(SR * 0.5))
    x[:len(boing)] += boing
    i = int(SR * 0.3)
    x[i:i + len(stab)] += stab
    write("SFX_TrapSpringPop", x)


def build_trap_mallet_swing():
    tt = t(0.35)
    whoosh = (lowpass(noise(0.35), 5) - lowpass(noise(0.35), 30)) * np.sin(np.pi * np.linspace(0, 1, len(tt))) ** 2
    bonk = sweep(400, 90, 0.2) * env(int(SR * 0.2), 0.001, 0.04) + 0.5 * lowpass(noise(0.2), 15) * env(int(SR * 0.2), 0.001, 0.03)
    x = np.zeros(int(SR * 0.6))
    x[:len(whoosh)] += 0.6 * whoosh
    i = int(SR * 0.32)
    x[i:i + len(bonk)] += bonk
    write("SFX_TrapMalletSwing", x)


def build_turret_fire():
    n = int(SR * 0.15)
    crack = lowpass(noise(0.15), 2) * env(n, 0.0003, 0.01)
    boom = sweep(300, 90, 0.15) * env(n, 0.0005, 0.03)
    x = crack + 0.8 * boom
    write("SFX_TurretFire", x)


def build_breach_thud():
    n = int(SR * 0.4)
    x = sweep(120, 40, 0.4) * env(n, 0.001, 0.1) + 0.6 * lowpass(noise(0.4), 25) * env(n, 0.001, 0.05)
    write("SFX_BreachThud", x)


def build_breach_break():
    total = int(SR * 1.2)
    x = np.zeros(total)
    crack1 = lowpass(noise(0.3), 2) * env(int(SR * 0.3), 0.001, 0.06)
    crack2 = lowpass(noise(0.25), 2) * env(int(SR * 0.25), 0.001, 0.05)
    crash = lowpass(noise(0.7), 10) * env(int(SR * 0.7), 0.005, 0.2)
    for i, seg in [(0.0, crack1), (0.2, crack2), (0.35, crash)]:
        s = int(SR * i)
        x[s:s + len(seg)] += seg[:total - s]
    write("SFX_BreachBreak", x)


def build_ammo_pickup():
    n = int(SR * 0.15)
    rattle1 = click(2800, dur=0.05, k=1, d=0.012)
    rattle2 = click(3200, dur=0.05, k=1, d=0.012)
    total = int(SR * 0.4)
    x = np.zeros(total)
    for i, seg in [(0.0, rattle1), (0.1, rattle2), (0.18, rattle1)]:
        s = int(SR * i)
        x[s:s + len(seg)] += seg[:total - s]
    write("SFX_AmmoPickup", x)


def bandpass(x, f_lo, f_hi):
    """Cheap band-pass via difference of two moving-average lowpasses."""
    k_hi = max(1, int(SR / f_hi))
    k_lo = max(2, int(SR / f_lo))
    return lowpass(x, k_hi) - lowpass(x, k_lo)


def formant_saw(f0_arr, formants, weights):
    ph = 2 * np.pi * np.cumsum(f0_arr) / SR
    saw = 2 * ((ph / (2 * np.pi)) % 1) - 1
    out = np.zeros_like(saw)
    for (f_lo, f_hi), w in zip(formants, weights):
        out += w * bandpass(saw, f_lo, f_hi)
    return out


def simlish_syllable(f0_start, f0_end, dur, formants, weights, attack=0.01, decay=None, rough=0.0):
    n = int(SR * dur)
    f0_arr = np.linspace(f0_start, f0_end, n)
    v = formant_saw(f0_arr, formants, weights)
    if rough:
        v = v * (1.0 - rough) + rough * np.sign(v)
    return v * env(n, attack, decay or dur * 0.55)


def simlish_phrase(syllables, gap=0.02):
    total = sum(len(s) for s in syllables) + int(SR * gap) * (len(syllables) - 1)
    x = np.zeros(total)
    i = 0
    for seg in syllables:
        x[i:i + len(seg)] += seg
        i += len(seg) + int(SR * gap)
    return x


HAPPY_FORMANTS = [(450, 750), (1700, 2300)]  # bright "ee"/"ay" vowel


def build_simlish_happy_01():
    bases = [260, 300, 340]
    durs = [0.11, 0.13, 0.15]
    syls = [simlish_syllable(b, b * 1.25, d, HAPPY_FORMANTS, [1.0, 0.6])
            for b, d in zip(bases, durs)]
    write("SFX_Simlish_Happy_01", simlish_phrase(syls))


def build_simlish_happy_02():
    bases = [240, 270, 300, 330]
    durs = [0.07, 0.08, 0.09, 0.11]
    syls = [simlish_syllable(b, b * 1.2, d, HAPPY_FORMANTS, [1.0, 0.55])
            for b, d in zip(bases, durs)]
    write("SFX_Simlish_Happy_02", simlish_phrase(syls))


def build_simlish_happy_03():
    bases = [280, 300, 330, 360, 400]
    durs = [0.07, 0.075, 0.08, 0.09, 0.10]
    syls = [simlish_syllable(b, b * 1.3, d, HAPPY_FORMANTS, [1.0, 0.6])
            for b, d in zip(bases, durs)]
    write("SFX_Simlish_Happy_03", simlish_phrase(syls))


ANNOYED_FORMANTS = [(400, 650), (900, 1300)]  # duller "uh"/"oh" vowel


def build_simlish_annoyed_01():
    bases = [190, 165, 150]
    durs = [0.11, 0.12, 0.10]
    syls = [simlish_syllable(b, b * 0.85, d, ANNOYED_FORMANTS, [1.0, 0.5], rough=0.25)
            for b, d in zip(bases, durs)]
    hmph = lowpass(noise(0.09), 8) * env(int(SR * 0.09), 0.002, 0.03)
    write("SFX_Simlish_Annoyed_01", simlish_phrase(syls + [hmph]))


def build_simlish_annoyed_02():
    bases = [175, 150, 140, 120]
    durs = [0.09, 0.10, 0.10, 0.13]
    syls = [simlish_syllable(b, b * 0.8, d, ANNOYED_FORMANTS, [1.0, 0.5], rough=0.3)
            for b, d in zip(bases, durs)]
    hmph = lowpass(noise(0.08), 8) * env(int(SR * 0.08), 0.002, 0.025)
    write("SFX_Simlish_Annoyed_02", simlish_phrase(syls + [hmph]))


def build_simlish_annoyed_03():
    bases = [170, 155]
    durs = [0.14, 0.16]
    syls = [simlish_syllable(b, b * 0.75, d, ANNOYED_FORMANTS, [1.0, 0.55], rough=0.35)
            for b, d in zip(bases, durs)]
    hmph = lowpass(noise(0.1), 7) * env(int(SR * 0.1), 0.002, 0.035)
    write("SFX_Simlish_Annoyed_03", simlish_phrase(syls + [hmph]))


HMM_FORMANTS = [(220, 340), (600, 850)]  # closed-mouth nasal hum


def build_simlish_hmm_01():
    n1 = int(SR * 0.22)
    n2 = int(SR * 0.26)
    mm = simlish_syllable(150, 150, 0.22, HMM_FORMANTS, [1.0, 0.3], attack=0.03, decay=0.3)
    hmm = simlish_syllable(150, 190, 0.26, HMM_FORMANTS, [1.0, 0.35], attack=0.02, decay=0.35)
    write("SFX_Simlish_Hmm_01", simlish_phrase([mm, hmm], gap=0.03))


def build_simlish_hmm_02():
    mm = simlish_syllable(165, 165, 0.18, HMM_FORMANTS, [1.0, 0.3], attack=0.03, decay=0.25)
    hmm = simlish_syllable(165, 210, 0.22, HMM_FORMANTS, [1.0, 0.35], attack=0.02, decay=0.3)
    write("SFX_Simlish_Hmm_02", simlish_phrase([mm, hmm], gap=0.025))


def build_simlish_hmm_03():
    mm = simlish_syllable(140, 140, 0.24, HMM_FORMANTS, [1.0, 0.3], attack=0.04, decay=0.32)
    hmm = simlish_syllable(140, 175, 0.28, HMM_FORMANTS, [1.0, 0.35], attack=0.02, decay=0.38)
    write("SFX_Simlish_Hmm_03", simlish_phrase([mm, hmm], gap=0.035))



BUILDERS = {
    "SFX_ScanBeep": build_scan_beep,
    "SFX_CashRegister": build_cash_register,
    "SFX_SocketSnap": build_socket_snap,
    "SFX_Repair": build_repair,
    "SFX_TrapZap": build_trap_zap,
    "SFX_TrapGasHiss": build_trap_gas_hiss,
    "SFX_TrapSpringPop": build_trap_spring_pop,
    "SFX_TrapMalletSwing": build_trap_mallet_swing,
    "SFX_TurretFire": build_turret_fire,
    "SFX_BreachThud": build_breach_thud,
    "SFX_BreachBreak": build_breach_break,
    "SFX_AmmoPickup": build_ammo_pickup,
    "SFX_Simlish_Happy_01": build_simlish_happy_01,
    "SFX_Simlish_Happy_02": build_simlish_happy_02,
    "SFX_Simlish_Happy_03": build_simlish_happy_03,
    "SFX_Simlish_Annoyed_01": build_simlish_annoyed_01,
    "SFX_Simlish_Annoyed_02": build_simlish_annoyed_02,
    "SFX_Simlish_Annoyed_03": build_simlish_annoyed_03,
    "SFX_Simlish_Hmm_01": build_simlish_hmm_01,
    "SFX_Simlish_Hmm_02": build_simlish_hmm_02,
    "SFX_Simlish_Hmm_03": build_simlish_hmm_03,
}


def main():
    args = sys.argv[1:]
    names = args if args else list(BUILDERS.keys())
    for name in names:
        if name not in BUILDERS:
            print("Unknown name:", name, "-- choices:", list(BUILDERS.keys()))
            continue
        BUILDERS[name]()


if __name__ == "__main__":
    main()
