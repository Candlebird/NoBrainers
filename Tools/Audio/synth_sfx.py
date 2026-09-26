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

    # --- Weapons (Phase 7 H) ---
    def gunshot(dur, f0, f1, crack_k, boom_decay, tail_k, crack=1.0, boom=1.0, tail=0.6):
        n = int(SR * dur)
        c = lowpass(noise(dur), crack_k) * env(n, 0.0005, 0.012)
        b = sweep(f0, f1, dur) * env(n, 0.001, boom_decay)
        tl = lowpass(noise(dur), tail_k) * env(n, 0.003, boom_decay * 2.5)
        return crack * c + boom * b + tail * tl

    guns = {
        'Pistol':      gunshot(0.35, 260, 70, 2, 0.05, 20),
        'Rifle':       gunshot(0.55, 200, 55, 1, 0.07, 30, crack=1.3),
        'Shotgun':     gunshot(0.8, 140, 40, 4, 0.12, 50, boom=1.4, tail=0.9),
        'SMG':         gunshot(0.18, 380, 120, 2, 0.025, 12, crack=0.9, tail=0.3),
        'LongRifle':   gunshot(1.0, 170, 40, 1, 0.1, 60, crack=1.5, tail=1.0),
        'Magnum':      gunshot(0.7, 180, 45, 2, 0.1, 40, boom=1.3),
        'LeverAction': gunshot(0.6, 210, 50, 1, 0.08, 35),
        'SawedOff':    gunshot(0.7, 110, 35, 6, 0.1, 70, boom=1.5, tail=1.1),
    }
    for g, x in guns.items():
        write('SFX_Fire_' + g, x, 0.95)

    def click(f, dur=0.05, k=2, d=0.008):
        n = int(SR * dur)
        return lowpass(noise(dur), k) * env(n, 0.0005, d) + 0.4 * np.sin(2 * np.pi * f * t(dur)) * env(n, 0.0005, d)

    def seq(total, events):
        x = np.zeros(int(SR * total))
        for at, seg in events:
            i = int(SR * at); x[i:i + len(seg)] += seg[:len(x) - i]
        return x

    slide = lambda d: lowpass(noise(d), 3) * env(int(SR * d), 0.02, d * 0.6) * 0.5
    reloads = {  # mag out, mag in, rack/slide
        'Pistol':      seq(0.9, [(0.0, click(1800)), (0.45, click(1400, k=3)), (0.7, slide(0.12)), (0.8, click(2200))]),
        'Rifle':       seq(1.4, [(0.0, click(1500, k=3)), (0.6, click(1200, k=4)), (1.0, slide(0.15)), (1.15, click(2000, 0.08))]),
        'SMG':         seq(1.1, [(0.0, click(1900)), (0.5, click(1600, k=3)), (0.85, click(2400))]),
        'LongRifle':   seq(1.6, [(0.0, click(1100, k=4)), (0.3, slide(0.2)), (0.8, click(1300, k=4)), (1.2, slide(0.2)), (1.4, click(1700, 0.08))]),
        'Magnum':      seq(1.5, [(0.0, click(900, k=5)), (0.25, slide(0.25)),
                                  (0.7, click(2600, 0.03)), (0.8, click(2500, 0.03)), (0.9, click(2700, 0.03)), (1.2, click(1000, k=5))]),
        'LeverAction': seq(1.3, [(0.0, click(2100, 0.04)), (0.3, click(2000, 0.04)), (0.6, click(2200, 0.04)),
                                  (0.95, slide(0.1)), (1.08, click(1300, 0.07, k=4))]),
        'Shotgun':     seq(1.5, [(0.0, click(1700, 0.05, k=3)), (0.35, click(1650, 0.05, k=3)), (0.7, click(1750, 0.05, k=3)),
                                  (1.1, slide(0.12)), (1.25, click(900, 0.1, k=6, d=0.03))]),
        'SawedOff':    seq(1.2, [(0.0, click(800, 0.1, k=6, d=0.03)), (0.4, click(1600, k=3)), (0.6, click(1600, k=3)),
                                  (0.95, click(700, 0.12, k=8, d=0.04))]),
    }
    for g, x in reloads.items():
        write('SFX_Reload_' + g, x, 0.7)

    # Melee whoosh: band-passed noise swelling then fading.
    tt = t(0.35)
    w = (lowpass(noise(0.35), 6) - lowpass(noise(0.35), 40)) * np.sin(np.pi * np.linspace(0, 1, len(tt))) ** 2
    write('SFX_MeleeWhoosh', w, 0.55)
    # Generic melee clang: inharmonic metallic partials + thud.
    tt = t(0.7)
    x = sum(a * np.sin(2 * np.pi * f * tt) for f, a in [(523, 1), (1187, .7), (1893, .5), (2741, .35), (3911, .2)])
    x = x * env(len(tt), 0.001, 0.12) + 0.8 * sweep(150, 60, 0.7) * env(len(tt), 0.001, 0.04) + 0.5 * lowpass(noise(0.7), 3) * env(len(tt), 0.0005, 0.01)
    write('SFX_MeleeClang', x, 0.85)

    # --- Zombies (Phase 7 H) ---
    def groan(dur, f0, f1, rough=0.5, jit=10, att=0.03, dec=None):
        tt = t(dur)
        f = np.linspace(f0, f1, len(tt)) + jit * lowpass(rng.uniform(-1, 1, len(tt)), 800) * 15
        ph = 2 * np.pi * np.cumsum(f) / SR
        v = np.sign(np.sin(ph)) * rough + np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sin(3 * ph)
        v = v * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * tt))  # vocal-fry flutter
        v = v + 0.35 * lowpass(noise(dur), 10)
        return lowpass(v, 10) * env(len(tt), att, dec or dur * 0.5)

    write('SFX_ZombieHurt', groan(0.4, 190, 120, rough=0.8, att=0.01, dec=0.15), 0.75)
    write('SFX_ZombieDeath', groan(1.4, 150, 55, rough=0.6, att=0.05, dec=0.6), 0.8)
    write('SFX_ZombieAttack', groan(0.7, 110, 170, rough=0.9, jit=14, att=0.06, dec=0.3), 0.8)


if __name__ == '__main__':
    main()
