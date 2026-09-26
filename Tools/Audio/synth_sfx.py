"""Synthesize crude placeholder SFX for No Brainers (Phase 7 F.4).

Writes 16-bit mono 44.1 kHz WAVs to PlaceholderAssets/Audio/. Each file name matches the
Unreal SoundWave name it's imported as, so a real (e.g. Freesound) sound can replace it
later by reimporting a file with the same name.
Run: python Tools/Audio/synth_sfx.py
"""
import os, wave
import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(__file__), '..', '..', 'PlaceholderAssets', 'Audio')
rng = np.random.default_rng(7)


def t(dur):
    return np.arange(int(SR * dur)) / SR


def env(n, attack=0.005, decay=None):
    """Linear attack, exponential decay envelope over n samples."""
    a = max(1, int(SR * attack))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    if decay:
        e[a:] = np.exp(-np.arange(n - a) / (SR * decay))
    return e


def noise(dur):
    return rng.uniform(-1, 1, int(SR * dur))


def lowpass(x, k):
    """Cheap moving-average lowpass; bigger k = darker."""
    return np.convolve(x, np.ones(k) / k, mode='same')


def sweep(f0, f1, dur, shape=np.sin):
    tt = t(dur)
    f = np.linspace(f0, f1, len(tt))
    return shape(2 * np.pi * np.cumsum(f) / SR)


def write(name, x, gain=0.8):
    x = x / (np.max(np.abs(x)) + 1e-9) * gain
    fade = min(len(x), int(SR * 0.01))
    x[-fade:] *= np.linspace(1, 0, fade)
    data = (x * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + '.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())
    print('wrote', name, f'{len(x)/SR:.2f}s')


def main():
    os.makedirs(OUT, exist_ok=True)

    # Dry-fire: two tight metallic ticks.
    n = noise(0.09) * env(int(SR * 0.09), 0.001, 0.006)
    tick = n + 0.5 * np.sin(2 * np.pi * 3200 * t(0.09)) * env(int(SR * 0.09), 0.001, 0.004)
    x = np.concatenate([tick, np.zeros(int(SR * 0.03)), 0.6 * tick])
    write('SFX_DryFire', x, 0.6)

    # Hitmarker tick: short high blip.
    x = np.sin(2 * np.pi * 2400 * t(0.06)) * env(int(SR * 0.06), 0.001, 0.015)
    write('SFX_Hitmarker', x, 0.5)

    # Headshot ding: bell-ish partials.
    tt = t(0.6)
    x = sum(a * np.sin(2 * np.pi * f * tt) for f, a in [(1760, 1), (2637, .5), (3520, .3), (4400, .15)])
    write('SFX_HeadshotDing', x * env(len(tt), 0.002, 0.18), 0.6)

    # Kill confirm: lower double blip.
    b = np.sin(2 * np.pi * 1100 * t(0.07)) * env(int(SR * 0.07), 0.001, 0.02)
    write('SFX_KillConfirm', np.concatenate([b, np.zeros(int(SR * .02)), b * 1.2]), 0.6)

    # Screamer shriek: rising screechy saw with vibrato + noise.
    tt = t(1.4)
    f = np.linspace(700, 1500, len(tt)) + 60 * np.sin(2 * np.pi * 9 * tt)
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = 2 * ((ph / (2 * np.pi)) % 1) - 1
    x = (saw + 0.4 * noise(1.4)) * env(len(tt), 0.08, 0.7)
    write('SFX_ScreamerShriek', lowpass(x, 3), 0.8)

    # Bloater swell: wet rising gurgle (AM noise).
    tt = t(1.5)
    g = lowpass(noise(1.5), 40) * (0.5 + 0.5 * np.sin(2 * np.pi * np.linspace(4, 14, len(tt)) * tt))
    x = g * np.linspace(0.2, 1, len(tt)) + 0.4 * sweep(60, 160, 1.5)
    write('SFX_BloaterSwell', x, 0.7)

    # Bloater pop: boom + splat.
    boom = sweep(120, 35, 0.8) * env(int(SR * 0.8), 0.002, 0.25)
    splat = lowpass(noise(0.8), 6) * env(int(SR * 0.8), 0.001, 0.08)
    write('SFX_BloaterPop', boom + 0.8 * splat, 0.95)

    # Acid glob launch (spit) and splat.
    x = lowpass(noise(0.35), 4) * env(int(SR * .35), 0.01, 0.08) + 0.3 * sweep(500, 200, .35) * env(int(SR * .35), .005, .1)
    write('SFX_SpitterSpit', x, 0.7)
    x = lowpass(noise(0.6), 12) * env(int(SR * .6), 0.001, 0.12)
    write('SFX_AcidSplat', x, 0.7)
    # Acid sizzle loop (1s, loopable-ish).
    x = (noise(1.0) - lowpass(noise(1.0), 8)) * (0.7 + 0.3 * rng.uniform(0, 1, SR))
    write('SFX_AcidSizzle', x, 0.35)

    # Brute charge roar: low growl with jittered pitch.
    tt = t(1.3)
    f = 85 + 15 * lowpass(rng.uniform(-1, 1, len(tt)), 2000) * 20
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sign(np.sin(ph)) * 0.6 + np.sin(ph * 2)) * env(len(tt), 0.1, 0.8) + 0.3 * lowpass(noise(1.3), 20)
    write('SFX_BruteRoar', lowpass(x, 8), 0.9)
    # Brute impact thud.
    write('SFX_BruteImpact', sweep(90, 30, 0.5) * env(int(SR * .5), .001, .15) + 0.5 * lowpass(noise(.5), 30) * env(int(SR * .5), .001, .05), 0.95)

    # Surge warning groan: distant chorus of low detuned moans.
    tt = t(3.0)
    x = np.zeros(len(tt))
    for base in (70, 83, 97, 110, 131):
        f = base * (1 + 0.08 * np.sin(2 * np.pi * rng.uniform(.2, .6) * tt + rng.uniform(0, 6)))
        x += np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    x = lowpass(x + 0.5 * lowpass(noise(3.0), 60), 30) * env(len(tt), 0.8, 1.6)
    write('SFX_SurgeGroan', x, 0.8)

    # Zombie ground-claw spawn: gritty dirt crunches.
    x = np.zeros(int(SR * 1.2))
    for s in (0.0, 0.25, 0.45, 0.7, 0.95):
        seg = lowpass(noise(0.18), 5) * env(int(SR * .18), .002, .04)
        i = int(SR * s); x[i:i + len(seg)] += seg[:len(x) - i]
    write('SFX_ZombieDigOut', x, 0.6)

    # Player hurt thump (for damage vignette).
    write('SFX_PlayerHurt', sweep(160, 60, .25) * env(int(SR * .25), .002, .07), 0.7)


if __name__ == '__main__':
    main()
