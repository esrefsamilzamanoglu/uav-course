"""Install and start this course's native Ubuntu Gazebo/SITL environment."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / ".local"
SOURCE = LOCAL / "ardupilot_gazebo"
BUILD = SOURCE / "build-linux"
PREFIX = ROOT / ".pixi/envs/default"
SITL = LOCAL / "sitl"
WORLD = LOCAL / "iris.sdf"
GUI = LOCAL / "iris_gui.config"
COMMIT = "082a0fe231f6e63bc8d1598f1cba461d9e2ea7f5"
DOWNLOADS = json.loads((ROOT / "downloads.json").read_text())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked(*args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def pixi():
    executable = os.environ.get("UAV_COURSE_PIXI") or shutil.which("pixi")
    if not executable:
        executable = str(Path.home() / ".pixi/bin/pixi")
    if not Path(executable).is_file():
        raise RuntimeError("Pixi bulunamadi. Once bash linux/kur.sh calistirin.")
    return [executable, "run", "--manifest-path", str(ROOT / "pixi.toml")]


def environment():
    env = os.environ.copy()
    env.update(GZ_VERSION="jetty", GZ_PARTITION="uav_course_linux",
               GZ_SIM_SYSTEM_PLUGIN_PATH=str(BUILD),
               GZ_SIM_RESOURCE_PATH=str(SOURCE / "models"))
    return env


def desktop_environment():
    # QGroundControl bundles its own Qt; do not inherit a conda/Pixi Qt stack.
    env = os.environ.copy()
    for key in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QML2_IMPORT_PATH",
                "QML_IMPORT_PATH", "LD_LIBRARY_PATH", "LD_PRELOAD"):
        env.pop(key, None)
    return env


def download(entry):
    target = LOCAL / entry["file"]
    if target.is_file() and digest(target) == entry["sha256"]:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".download")
    for attempt in range(3):
        try:
            request = urllib.request.Request(entry["url"], headers={"User-Agent": "uav-course"})
            with urllib.request.urlopen(request, timeout=60) as source, partial.open("wb") as out:
                shutil.copyfileobj(source, out)
            if digest(partial) != entry["sha256"]:
                raise RuntimeError(f"Indirme surumu degismis: {entry['file']}. Ders sorumlusuna bildirin.")
            partial.replace(target)
            return
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2)
        finally:
            partial.unlink(missing_ok=True)


def install():
    LOCAL.mkdir(exist_ok=True)
    env = environment()
    print("[1/3] Resmi Gazebo eklentisi hazirlaniyor...", flush=True)
    if not SOURCE.exists():
        checked("git", "init", SOURCE)
        checked("git", "-C", SOURCE, "remote", "add", "origin",
                "https://github.com/ArduPilot/ardupilot_gazebo.git")
    checked("git", "-C", SOURCE, "config", "core.autocrlf", "false")
    head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "--verify", "HEAD"],
                          capture_output=True, text=True)
    if head.returncode:
        checked("git", "-C", SOURCE, "fetch", "--depth", "1", "origin", COMMIT)
        checked("git", "-C", SOURCE, "-c", "advice.detachedHead=false", "checkout", "--detach", "FETCH_HEAD")
    elif head.stdout.strip() != COMMIT:
        raise RuntimeError("Eklenti kaynak surumu farkli; .local/ardupilot_gazebo klasorunu kontrol edin.")
    patch = ROOT / "linux-core.patch"
    applied = subprocess.run(["git", "-C", str(SOURCE), "apply", "--reverse", "--check", str(patch)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if not applied:
        checked("git", "-C", SOURCE, "apply", "--check", patch)
        checked("git", "-C", SOURCE, "apply", patch)
    checked("cmake", "-S", SOURCE, "-B", BUILD, "-G", "Ninja",
            "-DBUILD_GSTREAMER_PLUGIN=OFF", "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
            f"-DCMAKE_PREFIX_PATH={PREFIX}", env=env)
    checked("cmake", "--build", BUILD, "--target", "ArduPilotPlugin", "--parallel", "2", env=env)
    print("[2/3] Resmi ArduCopter 4.7.2 ve QGroundControl 5.1.5 indiriliyor...", flush=True)
    for entry in DOWNLOADS:
        download(entry)
    (SITL / "arducopter").chmod(0o755)
    appimage = LOCAL / "qgc/QGroundControl.AppImage"
    appimage.chmod(0o755)
    app = appimage.parent / "squashfs-root/AppRun"
    if not app.is_file():
        checked(appimage, "--appimage-extract", cwd=appimage.parent,
                env=desktop_environment(), stdout=subprocess.DEVNULL)
    print("[3/3] Iris dunyasi ve kamera hazirlaniyor...", flush=True)
    checked(sys.executable, ROOT.parent / "windows/resolve_world.py", "--source",
            ROOT.parent / "windows/iris.sdf", "--models", SOURCE / "models", "--output", WORLD,
            stdout=subprocess.DEVNULL)
    checked("gz", "sdf", "-k", WORLD, env=env)
    gui = (PREFIX / "share/gz/gz-sim/gui/gui.config").read_text()
    gui, count = re.subn(r"<camera_pose>[^<]+</camera_pose>",
                        "<camera_pose>6 -6 4 0 0.45 2.35619449019</camera_pose>", gui)
    if count != 1:
        raise RuntimeError("Gazebo kamera ayari bulunamadi.")
    GUI.write_text(gui)
    checked("gz", "sim", "--versions", env=env)
    print("Kurulum tamamlandi. bash linux/baslat.sh --qgc calistirin.")


def port_free(port, kind):
    with socket.socket(socket.AF_INET, kind) as probe:
        if kind == socket.SOCK_STREAM:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def stop(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def start(args):
    for required in (BUILD / "libArduPilotPlugin.so", WORLD, GUI):
        if not required.is_file():
            raise RuntimeError("Once bash linux/kur.sh calistirin.")
    for entry in DOWNLOADS:
        file = LOCAL / entry["file"]
        if not file.is_file() or digest(file) != entry["sha256"]:
            raise RuntimeError(f"Eksik/degismis dosya: {entry['file']}. bash linux/kur.sh calistirin.")
    if not port_free(5760, socket.SOCK_STREAM) or not port_free(9002, socket.SOCK_DGRAM):
        raise RuntimeError("5760 veya 9002 portu kullanimda. Acik simulasyon oturumunu kapatin.")
    if not args.headless and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise RuntimeError("Gazebo icin Ubuntu masaustu oturumu gerekli.")
    logs = LOCAL / "logs"
    logs.mkdir(exist_ok=True)
    run = SITL / "run"
    run.mkdir(exist_ok=True)
    owned = []

    def launch(command, name, env, cwd=ROOT):
        with (logs / f"{name}.log").open("w") as output:
            child = subprocess.Popen([str(a) for a in command], cwd=cwd, env=env,
                                     stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        owned.append(child)
        return child

    def interrupted(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    try:
        command = pixi() + ["gz", "sim", "-r", "-v3"]
        command += ["-s"] if args.headless else ["--gui-config", str(GUI)]
        gazebo = launch(command + [str(WORLD)], "gazebo", environment())
        print("Gazebo aciliyor...", flush=True)
        deadline = time.monotonic() + 90
        while port_free(9002, socket.SOCK_DGRAM):
            if gazebo.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError(f"Gazebo eklentisi baslatilamadi. Ayrinti: {logs / 'gazebo.log'}")
            time.sleep(0.5)
        defaults = ",".join(str(SITL / "default_params" / f) for f in ("copter.parm", "gazebo-iris.parm"))
        sitl = launch([SITL / "arducopter", "--model", "JSON", "--speedup", "1", "--defaults", defaults,
                       "--serial0", "tcp:0", "--base-port", "5760", "--sim-address", "127.0.0.1",
                       "--sim-port-out", "9002"], "sitl", desktop_environment(), run)
        qgc = None
        if args.qgc and not args.headless:
            qgc = launch([LOCAL / "qgc/squashfs-root/AppRun"], "qgroundcontrol", desktop_environment())
        print("QGroundControl: TCP -> 127.0.0.1 -> 5760", flush=True)
        print("Bu terminal acik kalsin. Bitirince Gazebo'yu kapatin veya Ctrl+C kullanin.", flush=True)
        while gazebo.poll() is None and sitl.poll() is None:
            if qgc is not None and qgc.poll() not in (None, 0):
                raise RuntimeError(f"QGroundControl kapandi. Ayrinti: {logs / 'qgroundcontrol.log'}")
            time.sleep(0.5)
        if sitl.returncode not in (None, 0):
            raise RuntimeError(f"ArduCopter kapandi. Ayrinti: {logs / 'sitl.log'}")
    finally:
        for process in reversed(owned):
            stop(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["kur", "baslat"])
    parser.add_argument("--qgc", action="store_true", help="QGroundControl'u da ac")
    parser.add_argument("--headless", action="store_true", help="Gazebo sunucusunu penceresiz calistir")
    args = parser.parse_args()
    try:
        install() if args.action == "kur" else start(args)
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Islem durdu: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
