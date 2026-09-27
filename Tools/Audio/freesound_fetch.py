"""Search and download original-quality WAVs from Freesound for No Brainers.

Reuses the OAuth2 token saved by freesound_oauth.py (see that scripts
_load_token/cmd_whoami for the request shape). Never prints the token.

Usage (run from repo root):
    python Tools/Audio/freesound_fetch.py search "<query>" --max-dur <sec>
        Searches Freesound for WAV files under <sec> seconds. Prints one
        line per hit, but only for CC0 or CC BY 4.0 licensed sounds.

    python Tools/Audio/freesound_fetch.py download <id> <sfx_name> [--trim <sec>]
        Downloads sound <id> (original quality) to
        PlaceholderAssets/Audio/<sfx_name>.wav, refuses non-wav types, and
        upserts an entry into freesound_sources.json. If --trim is given,
        cuts the file to that length (from the start) with a 30ms fade-out
        using only stdlib wave + numpy (no ffmpeg/pydub/soundfile).
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import wave

import numpy as np

HERE = os.path.dirname(__file__)
TOKEN_PATH = os.path.join(HERE, ".freesound_token.json")
SOURCES_PATH = os.path.join(HERE, "freesound_sources.json")
AUDIO_DIR = os.path.join(HERE, "..", "..", "PlaceholderAssets", "Audio")

SEARCH_URL = "https://freesound.org/apiv2/search/text/"
SOUND_URL_TMPL = "https://freesound.org/apiv2/sounds/{}/"
DOWNLOAD_URL_TMPL = "https://freesound.org/apiv2/sounds/{}/download/"

ALLOWED_LICENSE_MARKERS = ("/zero/", "/by/4.0/")


def _load_token():
    if not os.path.exists(TOKEN_PATH):
        sys.exit("No saved token at {}. Run freesound_oauth.py authorize/exchange first.".format(TOKEN_PATH))
    with open(TOKEN_PATH) as f:
        return json.load(f)


def _auth_headers():
    token = _load_token()
    return {"Authorization": "Bearer {}".format(token["access_token"])}


def _get_json(url, headers):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit("{} -> HTTP {}: {}".format(url, e.code, e.read().decode(errors="replace")))


def cmd_search(query, max_dur):
    headers = _auth_headers()
    params = {
        "query": query,
        "filter": "type:wav duration:[0.05 TO {}]".format(max_dur),
        "fields": "id,name,username,license,duration,type,url",
        "page_size": 30,
    }
    url = SEARCH_URL + "?" + urllib.parse.urlencode(params)
    data = _get_json(url, headers)
    results = data.get("results", [])
    shown = 0
    for r in results:
        lic = r.get("license", "")
        if not any(marker in lic for marker in ALLOWED_LICENSE_MARKERS):
            continue
        shown += 1
        print("id={} dur={:.2f}s user={} license={} name={!r} url={}".format(
            r["id"], r["duration"], r["username"], lic, r["name"], r["url"]))
    if shown == 0:
        print("No CC0/CC-BY-4.0 wav results found.")


def _upsert_source(entry):
    if os.path.exists(SOURCES_PATH):
        with open(SOURCES_PATH) as f:
            sources = json.load(f)
    else:
        sources = []
    sources = [s for s in sources if s.get("sfx_name") != entry["sfx_name"]]
    sources.append(entry)
    with open(SOURCES_PATH, "w") as f:
        json.dump(sources, f, indent=2)
        f.write("\n")


def _trim_wav(path, seconds, fade_ms=30):
    with wave.open(path, "rb") as w:
        n_channels = w.getnchannels()
        sampwidth = w.getsampwidth()
        framerate = w.getframerate()
        n_frames = w.getnframes()
        raw = w.readframes(n_frames)

    dtype = None
    if sampwidth == 2:
        dtype = np.int16
        maxval = 32767
        data = np.frombuffer(raw, dtype=dtype)
    elif sampwidth == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        as_i32 = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) |
                  (b[:, 2].astype(np.int32) << 16))
        as_i32[as_i32 >= (1 << 23)] -= (1 << 24)
        data = as_i32
        maxval = (1 << 23) - 1
    else:
        print("Skipping trim: unsupported sample width {} bytes.".format(sampwidth))
        return

    if n_channels > 1:
        data = data.reshape(-1, n_channels)

    keep_frames = int(seconds * framerate)
    data = data[:keep_frames]

    fade_frames = min(len(data), int(framerate * fade_ms / 1000))
    if fade_frames > 0:
        fade_curve = np.linspace(1.0, 0.0, fade_frames)
        data = data.astype(np.float64)
        if data.ndim == 2:
            data[-fade_frames:] *= fade_curve[:, None]
        else:
            data[-fade_frames:] *= fade_curve
        data = np.clip(data, -maxval - 1, maxval)

    if sampwidth == 2:
        out_bytes = data.astype(np.int16).tobytes()
    else:
        flat = data.astype(np.int32).reshape(-1)
        out_bytes = bytearray()
        for v in flat:
            out_bytes += int(v).to_bytes(3, byteorder="little", signed=True)
        out_bytes = bytes(out_bytes)

    with wave.open(path, "wb") as w:
        w.setnchannels(n_channels)
        w.setsampwidth(sampwidth)
        w.setframerate(framerate)
        w.writeframes(out_bytes)
    print("Trimmed {} to {}s with {}ms fade-out.".format(path, seconds, fade_ms))


def cmd_download(sound_id, sfx_name, trim):
    headers = _auth_headers()
    info = _get_json(SOUND_URL_TMPL.format(sound_id) + "?fields=id,name,username,license,duration,type,url", headers)
    if info.get("type") != "wav":
        sys.exit("Refusing download: sound {} type is {!r}, not wav.".format(sound_id, info.get("type")))

    req = urllib.request.Request(DOWNLOAD_URL_TMPL.format(sound_id), headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as e:
        sys.exit("download -> HTTP {}: {}".format(e.code, e.read().decode(errors="replace")))

    os.makedirs(AUDIO_DIR, exist_ok=True)
    out_path = os.path.join(AUDIO_DIR, sfx_name + ".wav")
    with open(out_path, "wb") as f:
        f.write(payload)
    print("Wrote {}".format(out_path))

    if trim:
        _trim_wav(out_path, trim)

    lic = info.get("license", "")
    _upsert_source({
        "sfx_name": sfx_name,
        "freesound_id": info["id"],
        "title": info["name"],
        "author": info["username"],
        "license": lic,
        "attribution_required": "/zero/" not in lic,
        "url": info.get("url", "https://freesound.org/s/{}/".format(sound_id)),
        "duration_seconds": info.get("duration"),
    })
    print("Updated {} with entry for {}.".format(SOURCES_PATH, sfx_name))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search")
    p_search.add_argument("query")
    p_search.add_argument("--max-dur", type=float, default=5.0)

    p_dl = sub.add_parser("download")
    p_dl.add_argument("id", type=int)
    p_dl.add_argument("sfx_name")
    p_dl.add_argument("--trim", type=float, default=None)

    args = parser.parse_args()
    if args.cmd == "search":
        cmd_search(args.query, args.max_dur)
    elif args.cmd == "download":
        cmd_download(args.id, args.sfx_name, args.trim)


if __name__ == "__main__":
    main()
