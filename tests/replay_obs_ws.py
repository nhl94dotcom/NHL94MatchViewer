"""The replay overlay's OBS WebSocket mode against a stand-in OBS (2026-11-13).

A small server speaking obs-websocket 5 (Hello with an authentication challenge, Identify checked against the
password, GetMediaInputStatus answered with a video position held still, as if the video were paused there) and
headless Edge loading overlay.html?replay=1&obs=Video&obspw=... from a folder with a replay pack, in real time through
its debugging port (a fast-forwarded --dump-dom snapshot races the network). The overlay must authenticate, ask for the
right Media Source and show the score for the position (read from the page until it appears, 10 s at most). Then the
stand-in moves the position on and the overlay must follow, and a wrong password must be refused.

python tests/replay_obs_ws.py PACK_FOLDER SECONDS:HOME-AWAY ...   (e.g. 2150:2-2 2151.5:2-3; the folder holds
replay_data.js; overlay.html is copied in from the repo). The seconds are checked in order, on one page."""
import asyncio
import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parents[1]
PASSWORD, SALT, CHALLENGE = "test-pass", "c2FsdA==", "Y2hhbGxlbmdl"
EDGE = next(p for p in (Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")) if p.exists())
PORT = 9333


def b64sha(text):
    return base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()


EXPECTED_AUTH = b64sha(b64sha(PASSWORD + SALT) + CHALLENGE)


class FakeObs:
    def __init__(self):
        self.cursor_ms, self.log = 0, []

    async def handler(self, ws):
        await ws.send(json.dumps({"op": 0, "d": {"obsWebSocketVersion": "5.0.0", "rpcVersion": 1,
                                                 "authentication": {"challenge": CHALLENGE, "salt": SALT}}}))
        ident = json.loads(await ws.recv())
        if not (ident["op"] == 1 and ident["d"].get("authentication") == EXPECTED_AUTH):
            self.log.append("auth WRONG")
            await ws.close(4009, "Authentication failed")
            return
        self.log.append("auth ok")
        await ws.send(json.dumps({"op": 2, "d": {"negotiatedRpcVersion": 1}}))
        try:
            async for msg in ws:
                req = json.loads(msg)["d"]
                self.log.append(f"{req['requestType']} {req.get('requestData', {}).get('inputName')}")
                await ws.send(json.dumps({"op": 7, "d": {
                    "requestType": req["requestType"], "requestId": req["requestId"],
                    "requestStatus": {"result": True, "code": 100},
                    "responseData": {"mediaState": "OBS_MEDIA_STATE_PAUSED", "mediaDuration": 2209000,
                                     "mediaCursor": self.cursor_ms}}}))
        except websockets.ConnectionClosed:
            pass


async def page_text(cdp, expr):
    await cdp.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True}}))
    while True:
        r = json.loads(await cdp.recv())
        if r.get("id") == 1:
            return r["result"]["result"].get("value")


async def run(folder, checks, password):
    obs = FakeObs()
    server = await websockets.serve(obs.handler, "127.0.0.1", 4455)
    url = (folder / "overlay.html").as_uri() + f"?replay=1&obs=Video&obspw={password}&stats=shots"
    profile = tempfile.mkdtemp(prefix="replay_obs_")
    edge = subprocess.Popen([str(EDGE), "--headless=new", "--disable-gpu", f"--remote-debugging-port={PORT}",
                             f"--user-data-dir={profile}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok = True
    try:
        target = None
        for _ in range(50):
            try:
                pages = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json").read())
                target = next((p for p in pages if p.get("type") == "page" and "overlay.html" in p.get("url", "")), None)
                if target:
                    break
            except OSError:
                pass
            await asyncio.sleep(0.2)
        async with websockets.connect(target["webSocketDebuggerUrl"], max_size=None) as cdp:
            for seconds, want in checks:
                obs.cursor_ms = int(seconds * 1000)
                shown = None
                for _ in range(40):
                    await asyncio.sleep(0.25)
                    txt = await page_text(cdp, "(document.querySelector('.score')||{}).textContent || "
                                               "(document.querySelector('.waiting')||{}).textContent || ''")
                    shown = "-".join(re.findall(r"\d+", txt)) or txt
                    if shown == want or (not want and len(txt) > 30):
                        break
                good = shown == want or (not want and not re.fullmatch(r"\d+-\d+", shown))
                ok &= good
                print(f"{seconds:8.1f} s: want {want or '(refused)'}: shows {shown!r}: {'OK' if good else 'FAILED'}")
    finally:
        edge.terminate()
        server.close()
        await server.wait_closed()
        shutil.rmtree(profile, ignore_errors=True)
    asked = sum("GetMediaInputStatus Video" in x for x in obs.log)
    print(f"  stand-in OBS: {obs.log[0] if obs.log else 'no connection'}, {asked} position requests")
    return ok, obs.log


def main():
    folder = Path(sys.argv[1]).resolve()
    shutil.copy(ROOT / "overlay.html", folder / "overlay.html")
    checks = [(float(a.split(":")[0]), a.split(":")[1]) for a in sys.argv[2:]]
    ok, log = asyncio.run(run(folder, checks, PASSWORD))
    ok &= bool(log) and log[0] == "auth ok"
    print("wrong password:")
    ok2, log2 = asyncio.run(run(folder, [(checks[0][0], "")], "not-the-password"))
    refused = bool(log2) and log2[0] == "auth WRONG" and not any("GetMediaInputStatus" in x for x in log2)
    print(f"  refused: {'OK' if refused else 'FAILED'}")
    sys.exit(0 if ok and refused else 1)


if __name__ == "__main__":
    main()
