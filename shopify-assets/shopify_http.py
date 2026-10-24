"""Shopify Admin GraphQL via direktes HTTP.

Token-Quelle (Priorität):
1. Client-ID + Client-Secret  — Dev-Dashboard-App, holt sich den Token
   selbst und erneuert ihn automatisch
2. shopify_token.txt          — dauerhafter shpat_-Token (alte Custom-App)
3. Shopify-CLI-Config         — Notfall-Fallback, läuft ab

GEÄNDERT GEGENÜBER DER VORVERSION
---------------------------------
1. Reihenfolge in `_load_token()` und `credentials_status()` korrigiert.
   Vorher stand die Token-Datei an erster Stelle: Sobald shopify_token.txt
   existierte und nicht leer war, kehrte die Funktion dort zurück und
   erreichte die Zugangsdaten nie. Eingetragene Client-ID/Secret blieben
   damit wirkungslos, und die Oberfläche meldete dauerhaft "ungültig".

2. Fehler werden nicht mehr verschluckt. `fetch_token_via_credentials()`
   fing jede Exception ab und gab "" zurück — die Antwort von Shopify,
   die den Grund nennt, ging verloren. Sie wird jetzt festgehalten und
   ist über `letzter_fehler()` abrufbar.

3. `pruefe_zugang()` ergänzt: prüft der Reihe nach alle Quellen und
   liefert einen lesbaren Bericht statt eines stillen Fehlschlags.

Die Signaturen aller bisherigen Funktionen sind unverändert, damit
app.py ohne Anpassung weiterläuft.
"""
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error

STORE = "zwergenladen-fr.myshopify.com"
API_VERSION = "2025-01"

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_TOKEN_FILE = os.path.join(_APP_DIR, "shopify_token.txt")
_CRED_FILE = os.path.join(_APP_DIR, "shopify_credentials.json")
_CACHE_FILE = os.path.join(_APP_DIR, "shopify_token_cache.json")
_CONFIG_PATH = os.path.expanduser(
    "~/Library/Preferences/shopify-cli-store-nodejs/config.json")

# Token vor Ablauf erneuern (Sicherheitspuffer in Sekunden)
_REFRESH_MARGIN = 600

# Letzte Fehlermeldung von Shopify — für die Anzeige in der Oberfläche
_LETZTER_FEHLER = ""


def letzter_fehler() -> str:
    """Klartext der letzten fehlgeschlagenen Token-Anforderung ('' wenn keine)."""
    return _LETZTER_FEHLER


def _merke_fehler(text: str) -> None:
    global _LETZTER_FEHLER
    _LETZTER_FEHLER = text


# ── Client-ID / Client-Secret (Dev-Dashboard-App) ────────────────────────────

def load_credentials() -> dict:
    """Liest client_id/client_secret aus shopify_credentials.json ({} wenn keine)."""
    if not os.path.exists(_CRED_FILE):
        return {}
    try:
        with open(_CRED_FILE) as f:
            cred = json.load(f)
    except Exception as e:
        _merke_fehler(f"shopify_credentials.json nicht lesbar: {e}")
        return {}
    if cred.get("client_id") and cred.get("client_secret"):
        return cred
    return {}


def save_credentials(client_id: str, client_secret: str) -> None:
    """Speichert die App-Zugangsdaten und verwirft den alten Token-Cache."""
    client_id = (client_id or "").strip()
    client_secret = (client_secret or "").strip()
    if not client_id or not client_secret:
        raise ValueError("Client-ID und Client-Secret dürfen nicht leer sein.")
    with open(_CRED_FILE, "w") as f:
        json.dump({"client_id": client_id, "client_secret": client_secret},
                  f, indent=2)
    try:
        os.chmod(_CRED_FILE, 0o600)
    except Exception:
        pass
    if os.path.exists(_CACHE_FILE):
        os.remove(_CACHE_FILE)
    _merke_fehler("")


def _read_cache() -> dict:
    try:
        with open(_CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _write_cache(token: str, expires_in: int) -> None:
    try:
        with open(_CACHE_FILE, "w") as f:
            json.dump({"access_token": token,
                       "expires_at": int(time.time()) + int(expires_in)},
                      f, indent=2)
        os.chmod(_CACHE_FILE, 0o600)
    except Exception:
        pass


def _token_anfordern(client_id: str, client_secret: str):
    """Ein Token-Request an Shopify.

    Rückgabe: (token, fehlertext). Genau eines von beidem ist gefüllt.
    Der Fehlertext enthält die Antwort von Shopify im Klartext — genau
    die Information, die vorher verschluckt wurde.
    """
    data = urllib.parse.urlencode({
        "client_id": (client_id or "").strip(),
        "client_secret": (client_secret or "").strip(),
        "grant_type": "client_credentials",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://{STORE}/admin/oauth/access_token", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        antwort = e.read().decode("utf-8", errors="replace")[:400]
        return "", f"Shopify antwortet HTTP {e.code}: {antwort}"
    except urllib.error.URLError as e:
        return "", f"Shop {STORE} nicht erreichbar: {e.reason}"
    except json.JSONDecodeError:
        return "", "Antwort von Shopify ist kein JSON"
    except Exception as e:
        return "", f"{type(e).__name__}: {e}"

    token = body.get("access_token", "")
    if not token:
        return "", f"Antwort ohne access_token: {json.dumps(body)[:300]}"
    return token, ""


def fetch_token_via_credentials(force: bool = False) -> str:
    """Holt einen Access-Token per Client-Credentials-Grant.

    Nutzt den zwischengespeicherten Token, solange er noch mindestens
    10 Minuten gültig ist. Gibt "" zurück, wenn keine Zugangsdaten
    hinterlegt sind oder Shopify den Grant ablehnt — der Grund steht
    dann in letzter_fehler().
    """
    cred = load_credentials()
    if not cred:
        return ""

    if not force:
        cache = _read_cache()
        if (cache.get("access_token")
                and cache.get("expires_at", 0) - _REFRESH_MARGIN > time.time()):
            return cache["access_token"]

    token, fehler = _token_anfordern(cred["client_id"], cred["client_secret"])
    if token:
        _write_cache(token, 86399)
        _merke_fehler("")
        return token

    _merke_fehler(fehler)
    return ""


def credentials_status() -> dict:
    """Status für die Oberfläche: Quelle, Gültigkeit, Ablaufzeitpunkt.

    Reihenfolge identisch mit _load_token() — sonst zeigt die Oberfläche
    eine andere Quelle an als die, die tatsächlich benutzt wird.
    """
    if load_credentials():
        cache = _read_cache()
        return {"source": "credentials",
                "expires_at": cache.get("expires_at"),
                "fehler": _LETZTER_FEHLER}
    if os.path.exists(_TOKEN_FILE) and open(_TOKEN_FILE).read().strip():
        return {"source": "token_file", "expires_at": None, "fehler": ""}
    return {"source": "cli", "expires_at": None, "fehler": ""}


# ── Token-Auflösung ──────────────────────────────────────────────────────────

def _load_token() -> str:
    """Liest den Shopify Admin API Token nach der Prioritätenliste oben.

    Zugangsdaten stehen bewusst VOR der Token-Datei: Wer Client-ID und
    Secret hinterlegt hat, will den automatisch erneuerten Token — nicht
    einen alten shpat_-Wert, der womöglich längst abgelaufen ist.
    """
    # 1. Client-ID + Secret → Token automatisch holen/erneuern
    token = fetch_token_via_credentials()
    if token:
        return token

    # 2. Dauerhafter Token aus Datei (alte Custom-App)
    if os.path.exists(_TOKEN_FILE):
        token = open(_TOKEN_FILE).read().strip()
        if token:
            return token

    # 3. CLI-Config-Fallback
    try:
        with open(_CONFIG_PATH) as f:
            config = json.load(f)
        for val in config.values():
            if not isinstance(val, dict):
                continue
            sessions = (val.get("myshopify", {})
                           .get("com", {})
                           .get("sessionsByUserId", {}))
            for session in sessions.values():
                token = session.get("accessToken", "")
                if token:
                    return token
    except Exception:
        pass

    grund = f"\n\nGrund der letzten Anfrage:\n{_LETZTER_FEHLER}" if _LETZTER_FEHLER else ""
    raise RuntimeError(
        "Kein Shopify-Zugang konfiguriert.\n\n"
        "Einmalig einrichten:\n"
        "1. Dev Dashboard öffnen: https://dev.shopify.com\n"
        "2. App 'Zwergenladen Import' → App-Einstellungen\n"
        "3. Client-ID und Client-Secret kopieren\n"
        "4. Beides in der Sidebar unter 'Shopify-Zugang' eintragen"
        + grund
    )


def save_token(token: str) -> None:
    """Speichert einen dauerhaften shpat_-Token in shopify_token.txt."""
    token = token.strip()
    if not token:
        raise ValueError("Leerer Token.")
    with open(_TOKEN_FILE, "w") as f:
        f.write(token)
    try:
        os.chmod(_TOKEN_FILE, 0o600)
    except Exception:
        pass


def test_token(token: str) -> bool:
    """Testet ob ein Token gültig ist. Gibt True zurück bei Erfolg."""
    url = f"https://{STORE}/admin/api/{API_VERSION}/graphql.json"
    q = json.dumps({"query": "{ shop { name } }"}).encode("utf-8")
    req = urllib.request.Request(url, data=q,
        headers={"Content-Type": "application/json",
                 "X-Shopify-Access-Token": token},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            return "shop" in data.get("data", {})
    except Exception:
        return False


def test_credentials(client_id: str, client_secret: str) -> bool:
    """Prüft Client-ID/Secret, ohne sie zu speichern.

    Bei Fehlschlag steht der Grund in letzter_fehler().
    """
    token, fehler = _token_anfordern(client_id, client_secret)
    _merke_fehler(fehler)
    return bool(token)


def pruefe_zugang() -> str:
    """Prüft alle Token-Quellen der Reihe nach und liefert einen Bericht.

    Zum Aufruf aus der Oberfläche oder direkt:
        python3 -c "import shopify_http; print(shopify_http.pruefe_zugang())"
    """
    zeilen = [f"Shop:        {STORE}",
              f"API-Version: {API_VERSION}",
              f"Ordner:      {_APP_DIR}",
              ""]

    cred = load_credentials()
    if cred:
        kid = cred["client_id"]
        zeilen.append(f"Zugangsdaten: vorhanden (Client-ID {kid[:8]}…{kid[-4:]})")
        token, fehler = _token_anfordern(cred["client_id"], cred["client_secret"])
        if token:
            zeilen.append("  Token holen: OK")
            zeilen.append(f"  Token testen: {'OK' if test_token(token) else 'ABGELEHNT'}")
        else:
            zeilen.append(f"  Token holen: FEHLGESCHLAGEN\n  {fehler}")
    else:
        zeilen.append("Zugangsdaten: keine (shopify_credentials.json fehlt "
                      "oder unvollständig)")

    if os.path.exists(_TOKEN_FILE):
        dateitoken = open(_TOKEN_FILE).read().strip()
        if dateitoken:
            gueltig = test_token(dateitoken)
            zeilen.append(f"shopify_token.txt: vorhanden, "
                          f"{'gültig' if gueltig else 'UNGÜLTIG'}")
            if not gueltig and not cred:
                zeilen.append("  → Datei löschen oder Zugangsdaten eintragen")
        else:
            zeilen.append("shopify_token.txt: vorhanden, aber leer")
    else:
        zeilen.append("shopify_token.txt: nicht vorhanden")

    zeilen.append(f"CLI-Config:  {'vorhanden' if os.path.exists(_CONFIG_PATH) else 'nicht vorhanden'}")
    return "\n".join(zeilen)


def _refresh_cli_token() -> bool:
    """Frischt den abgelaufenen CLI-Token per Refresh-Token auf.

    Führt einen harmlosen `shopify store execute`-Aufruf aus; die CLI erneuert
    dabei den accessToken in ihrer config.json automatisch (ohne Login), solange
    der Refresh-Token noch gültig ist. Gibt True bei Erfolg zurück.

    Greift nur, wenn weder ein permanenter Token noch Zugangsdaten existieren.
    """
    if os.path.exists(_TOKEN_FILE) or load_credentials():
        return False
    import shutil
    import subprocess
    shopify_bin = shutil.which("shopify") or "/opt/homebrew/bin/shopify"
    if not os.path.exists(shopify_bin):
        return False
    # fork-sicher (macOS Network.framework) — OBJC-Flag entfernen
    env = {k: v for k, v in os.environ.items()
           if k != "OBJC_DISABLE_INITIALIZE_FORK_SAFETY"}
    try:
        r = subprocess.run(
            [shopify_bin, "store", "execute", "--store", STORE,
             "--query", "query { shop { name } }"],
            capture_output=True, text=True, timeout=60, env=env, cwd="/tmp",
        )
        return r.returncode == 0
    except Exception:
        return False


def _do_request(query: str, variables: dict, token: str):
    """Führt einen einzelnen GraphQL-HTTP-Request aus. Wirft HTTPError bei 401."""
    url = f"https://{STORE}/admin/api/{API_VERSION}/graphql.json"
    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json",
                 "X-Shopify-Access-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read())


def execute(query: str, variables: dict = None) -> dict:
    """Führt eine Shopify Admin GraphQL Query/Mutation via HTTP aus.

    Bei 401 wird EINMAL automatisch ein frischer Token geholt (per
    Client-Credentials bzw. CLI-Refresh) und der Aufruf wiederholt.
    Gibt den `data`-Block zurück, oder {'_error': '...'}.
    """
    try:
        token = _load_token()
    except RuntimeError as e:
        return {"_error": str(e)}

    for _versuch in range(2):
        try:
            result = _do_request(query, variables, token)
            if "errors" in result:
                return {"_error": str(result["errors"])}
            return result.get("data", {})
        except urllib.error.HTTPError as e:
            if e.code == 401 and _versuch == 0:
                # a) Zugangsdaten vorhanden → Token erzwungen neu holen
                neu = fetch_token_via_credentials(force=True)
                if neu:
                    token = neu
                    continue
                # b) sonst CLI-Refresh versuchen
                if _refresh_cli_token():
                    try:
                        token = _load_token()
                        continue
                    except RuntimeError:
                        pass
            if e.code == 401:
                status = credentials_status()
                if status["source"] == "credentials":
                    hinweis = (
                        "Client-ID/Secret werden von Shopify abgelehnt.\n"
                        "Mögliche Gründe: Secret wurde im Dev Dashboard rotiert,\n"
                        "die App ist im Shop nicht (mehr) installiert, oder der\n"
                        "App-Version fehlen die nötigen Scopes.\n"
                        "→ Sidebar: 'Shopify-Zugang' neu eintragen.")
                    if _LETZTER_FEHLER:
                        hinweis += f"\n\nAntwort von Shopify:\n{_LETZTER_FEHLER}"
                elif status["source"] == "token_file":
                    hinweis = ("Der Token in shopify_token.txt ist ungültig.\n"
                               "→ Sidebar: 'Shopify-Zugang' neu einrichten.")
                else:
                    hinweis = ("CLI-Token abgelaufen und Erneuerung fehlgeschlagen.\n"
                               "Dauerhafte Lösung: Client-ID + Client-Secret in der\n"
                               "Sidebar unter 'Shopify-Zugang' eintragen.")
                return {"_error": f"Shopify-Zugriff verweigert (401).\n{hinweis}"}
            body = e.read().decode("utf-8", errors="replace")[:300]
            return {"_error": f"HTTP {e.code}: {body}"}
        except Exception as e:
            return {"_error": str(e)}
    return {"_error": "Unerwarteter Fehler bei der Shopify-Anfrage."}


if __name__ == "__main__":
    print(pruefe_zugang())
