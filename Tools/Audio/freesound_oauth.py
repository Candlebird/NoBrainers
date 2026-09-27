"""OAuth2 helper for the Freesound API (needed to download original-quality
sounds; the plain API key/token auth only gets you low-quality previews).

Freesound's OAuth2 app credentials are named "Client id" and "Client secret"
on their site, but the Client secret is the value they label "API key" on
the credential page. This script expects:
    FREESOUND_CLIENT_ID  - the app's Client id
    FREESOUND_API_KEY    - the app's Client secret ("API key")
both set as environment variables (never hard-code them here).

Usage:
    python Tools/Audio/freesound_oauth.py authorize
        Prints the URL to open in a browser. Log into Freesound, click
        "Authorize", and Freesound will show (or redirect with) a code.

    python Tools/Audio/freesound_oauth.py exchange <code>
        Exchanges the authorization code for an access/refresh token pair
        and saves them to Tools/Audio/.freesound_token.json (gitignored).

    python Tools/Audio/freesound_oauth.py refresh
        Uses the saved refresh token to get a new access token (access
        tokens expire in 24h; refresh tokens are one-time-use and rotate).

    python Tools/Audio/freesound_oauth.py whoami
        Sanity-checks the saved access token against /apiv2/me/.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

CLIENT_ID = os.environ.get('FREESOUND_CLIENT_ID')
CLIENT_SECRET = os.environ.get('FREESOUND_API_KEY')
TOKEN_PATH = os.path.join(os.path.dirname(__file__), '.freesound_token.json')

AUTHORIZE_URL = 'https://freesound.org/apiv2/oauth2/authorize/'
TOKEN_URL = 'https://freesound.org/apiv2/oauth2/access_token/'
ME_URL = 'https://freesound.org/apiv2/me/'


def _require_creds():
    if not CLIENT_ID or not CLIENT_SECRET:
        sys.exit('Set FREESOUND_CLIENT_ID and FREESOUND_API_KEY in the environment first.')


def _post(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f'{url} -> HTTP {e.code}: {e.read().decode(errors="replace")}')


def _save_token(payload):
    with open(TOKEN_PATH, 'w') as f:
        json.dump(payload, f, indent=2)
    print(f'Saved token to {TOKEN_PATH}')


def _load_token():
    if not os.path.exists(TOKEN_PATH):
        sys.exit(f'No saved token at {TOKEN_PATH}. Run "authorize" then "exchange <code>" first.')
    with open(TOKEN_PATH) as f:
        return json.load(f)


def cmd_authorize():
    _require_creds()
    url = f'{AUTHORIZE_URL}?client_id={CLIENT_ID}&response_type=code'
    print('Open this URL in a browser, log in, and click Authorize:')
    print(url)
    print()
    print('Freesound will show an authorization code on the page (or redirect')
    print('to your registered redirect URI with ?code=...). Copy that code, then run:')
    print('  python Tools/Audio/freesound_oauth.py exchange <code>')


def cmd_exchange(code):
    _require_creds()
    payload = _post(TOKEN_URL, {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
    })
    _save_token(payload)
    print('access_token expires in', payload.get('expires_in'), 'seconds.')
    print('refresh_token is one-time-use; this script rotates it automatically on "refresh".')


def cmd_refresh():
    _require_creds()
    token = _load_token()
    refresh_token = token.get('refresh_token')
    if not refresh_token:
        sys.exit('Saved token has no refresh_token. Re-run authorize/exchange.')
    payload = _post(TOKEN_URL, {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    })
    _save_token(payload)
    print('access_token refreshed, expires in', payload.get('expires_in'), 'seconds.')


def cmd_whoami():
    token = _load_token()
    req = urllib.request.Request(ME_URL, headers={
        'Authorization': f'Bearer {token["access_token"]}',
    })
    try:
        with urllib.request.urlopen(req) as resp:
            print(json.load(resp))
    except urllib.error.HTTPError as e:
        sys.exit(f'{ME_URL} -> HTTP {e.code}: {e.read().decode(errors="replace")}')


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    cmd, rest = args[0], args[1:]
    if cmd == 'authorize':
        cmd_authorize()
    elif cmd == 'exchange':
        if not rest:
            sys.exit('Usage: exchange <code>')
        cmd_exchange(rest[0])
    elif cmd == 'refresh':
        cmd_refresh()
    elif cmd == 'whoami':
        cmd_whoami()
    else:
        sys.exit(__doc__)
