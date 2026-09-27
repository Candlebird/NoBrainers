---
name: freesound-audio
description: Set up and use OAuth2 authentication for the Freesound API on No Brainers, so real (non-preview, original-quality) sounds can be downloaded to replace placeholder SFX. Use when asked to authorize/re-authorize Freesound, fetch/download a sound from Freesound, or when a Freesound access token has expired.
argument-hint: "[authorize | exchange <code> | refresh | whoami]"
---

Freesound's plain API-key/token auth only serves low-quality MP3 previews.
Downloading the original-quality file (the ones worth importing as a
`SoundWave` replacement for a placeholder) requires OAuth2, tied to a real
Freesound user account. This project's OAuth2 helper lives at
`Tools/Audio/freesound_oauth.py`.

## Credentials

Two environment variables must already be set (never hard-code them, never
print their raw values back into chat or commit them):

- `FREESOUND_CLIENT_ID` — the app's Client id.
- `FREESOUND_API_KEY` — the app's Client secret. Freesound's own UI labels
  this value "API key" on the credential page even though it functions as
  the OAuth2 client secret — don't be misled into thinking it's the simpler
  token-auth key.

If either is unset, stop and tell the user rather than guessing or asking
them to paste the raw secret into chat.

## Commands (run from repo root)

```
python Tools/Audio/freesound_oauth.py authorize        # prints the URL to open in a browser
python Tools/Audio/freesound_oauth.py exchange <code>   # exchanges the auth code for tokens
python Tools/Audio/freesound_oauth.py refresh            # rotates an expiring access token
python Tools/Audio/freesound_oauth.py whoami             # sanity-checks the saved token
```

Tokens save to `Tools/Audio/.freesound_token.json`, which is gitignored —
never commit it or paste its contents into chat.

## First-time authorization flow

This step needs the user's own Freesound login, so it cannot be completed
headlessly:

1. Run `authorize` and hand the printed URL to the user.
2. The user opens it, logs into Freesound, and clicks Authorize. Freesound
   shows (or redirects with) a short authorization code.
3. The user pastes that code back; run `exchange <code>` with it.
4. Run `whoami` to confirm the token resolves to their account before
   relying on it for downloads.

## Renewing an expired token

Access tokens last 24 hours (`expires_in` in the exchange/refresh output).
Refresh tokens are one-time-use and rotate automatically. If `whoami` fails
with an auth error, just run `refresh` — no user interaction needed unless
the refresh token itself has gone stale (rare; if `refresh` fails, redo the
full authorize/exchange flow above).

## Downloading a sound once authorized

Freesound's download endpoint is `GET /apiv2/sounds/<id>/download/` with
header `Authorization: Bearer <access_token>` (load the token from
`Tools/Audio/.freesound_token.json`). There's no wrapper script for this
yet — write a small one-off script using that pattern (see
`freesound_oauth.py`'s `_load_token`/`cmd_whoami` for the request shape) if
a builder needs to fetch a specific sound ID. Per the project's
`blender-authoring-preference` memory, only reach for a Freesound download
when the user has actually asked for a real-world sound source instead of a
synthesized placeholder — don't default to it.

After downloading, drop the file into `PlaceholderAssets/Audio/` under the
same filename as the placeholder it replaces, then re-run
`Tools/Audio/ue_import_sfx.py` (via Monolith `editor.run_python`) to
reimport it as the existing `SoundWave` asset in place.
