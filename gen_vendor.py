# -*- coding: utf-8 -*-
"""Download Flask + reportlab wheels (and deps) from PyPI JSON API and
unpack them into english-exam-grader/vendor/lib. Works around pip's
sandboxed temp-dir restrictions (plain urllib + zipfile writes work fine).
"""
import json
import os
import platform
import re
import sys
import urllib.request
import zipfile

VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "english-exam-grader", "vendor")
LIB = os.path.join(VENDOR, "lib")
os.makedirs(LIB, exist_ok=True)

PY_VER = "cp%d%d" % (sys.version_info.major, sys.version_info.minor)
ROOTS = ["flask", "reportlab"]
seen = set()
failures = []


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def eval_marker(marker):
    """Conservative evaluation of PEP 508 environment markers."""
    env = {
        "python_version": "%d.%d" % (sys.version_info.major, sys.version_info.minor),
        "python_full_version": platform.python_version(),
        "sys_platform": sys.platform,
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "os_name": os.name,
        "implementation_name": sys.implementation.name,
    }
    try:
        return eval(marker, {"__builtins__": {}}, env)
    except Exception:
        return False


def parse_req(req):
    """Return normalized package name if this requirement applies, else None."""
    req = req.strip()
    marker = None
    if ";" in req:
        req, marker = req.split(";", 1)
    if marker and not eval_marker(marker.strip()):
        return None
    m = re.match(r"^([A-Za-z0-9_.\-]+)", req.strip())
    if not m:
        return None
    return m.group(1).lower().replace("_", "-")


def pick_wheel(release_files):
    """Prefer pure wheels, then win_amd64 wheels for this CPython. Never macOS/linux."""
    pure = None
    win = None
    for f in release_files:
        if f.get("packagetype") != "bdist_wheel":
            continue
        fn = f["filename"]
        if "macosx" in fn or "linux" in fn or "manylinux" in fn or "musllinux" in fn:
            continue
        if "py3-none-any" in fn or "py2.py3-none-any" in fn:
            pure = pure or f
        elif "win_amd64" in fn and (PY_VER in fn or "abi3" in fn or "py3-" in fn):
            win = win or f
    return pure or win


def install(name):
    if name in seen:
        return
    seen.add(name)
    print("==> %s" % name)
    try:
        info = fetch_json("https://pypi.org/pypi/%s/json" % name)
    except Exception as e:
        failures.append((name, "metadata: %s" % e))
        return
    ver = info["info"]["version"]
    whl = pick_wheel(info["releases"].get(ver, []))
    if not whl:
        failures.append((name, "no compatible wheel for %s" % ver))
        return
    fn = whl["filename"]
    dest = os.path.join(VENDOR, fn)
    try:
        urllib.request.urlretrieve(whl["url"], dest)
        with zipfile.ZipFile(dest) as z:
            z.extractall(LIB)
        print("    installed %s" % fn)
    except Exception as e:
        failures.append((name, "download: %s" % e))
        return
    for r in info["info"].get("requires_dist") or []:
        dep = parse_req(r)
        if dep:
            install(dep)


for root in ROOTS:
    install(root)

print("\n--- done ---")
if failures:
    print("FAILURES:")
    for n, e in failures:
        print("  %s: %s" % (n, e))
    sys.exit(1)
else:
    print("all packages installed into %s" % LIB)
