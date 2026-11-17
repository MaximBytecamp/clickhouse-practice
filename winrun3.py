"""Съёмка для главы 0.1а (GitHub Actions, Windows с вложенной виртуализацией).

python winrun3.py desktop — Docker Desktop: приветствие, главное окно, стенд.
python winrun3.py planb   — без Docker Desktop: Docker Engine в Ubuntu (WSL), стенд,
                            запрос из Windows на localhost:8123."""
import os, pathlib, subprocess, sys, time, urllib.request, traceback
from PIL import ImageGrab
from pywinauto import Desktop

MODE = sys.argv[1]
OUT = pathlib.Path("shots-out").resolve(); OUT.mkdir(exist_ok=True)
LOG = open(OUT / f"log-{MODE}.txt", "a", encoding="utf-8")
N = [0]
ENV = {**os.environ, "WSL_UTF8": "1"}


def log(*a):
    t = " ".join(str(x) for x in a); print(t, flush=True); LOG.write(t + "\n"); LOG.flush()


def sh(cmd, timeout=1800):
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-c", cmd], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=ENV, timeout=timeout)
        log("$", cmd); log(r.stdout.rstrip()); log(r.stderr.rstrip()); log("код", r.returncode)
        return r
    except subprocess.TimeoutExpired:
        log("$", cmd, "— ТАЙМАУТ")


def wins(pred):
    out = []
    for w in Desktop(backend="uia").windows():
        try:
            if w.is_visible() and pred(w.window_text()):
                out.append(w)
        except Exception:
            pass
    return out


def snap_win(tag, w):
    N[0] += 1
    try:
        w.set_focus(); time.sleep(1.5)
        r = w.rectangle()
        ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom), all_screens=True).save(OUT / f"{MODE}-{N[0]:02d}-{tag}.png")
        texts = [f"{c.element_info.control_type}:{c.window_text()[:100]}" for c in w.descendants()
                 if c.window_text() and c.element_info.control_type in ("Button", "Text", "Hyperlink")]
        log("СНИМОК", tag, repr(w.window_text()), texts[:80])
    except Exception as e:
        log("не снялось", tag, e)


def screen(tag):
    N[0] += 1; ImageGrab.grab(all_screens=True).save(OUT / f"{MODE}-{N[0]:02d}-{tag}.png"); log("ЭКРАН", tag)


def hide_console():
    for w in Desktop(backend="win32").windows():
        try:
            if "hosted-compute-agent" in w.window_text() or "powershell" in w.window_text().lower():
                w.minimize()
        except Exception:
            pass


def click_link(w, text):
    for c in w.descendants():
        try:
            if c.window_text() == text and c.element_info.control_type in ("Hyperlink", "Button"):
                c.click_input(); log("НАЖАТО", text); return True
        except Exception:
            pass
    return False


def wait_url(url, seconds):
    t0 = time.time()
    while time.time() - t0 < seconds:
        try:
            return urllib.request.urlopen(url, timeout=5).read().decode()
        except Exception:
            time.sleep(5)


Q = "SELECT database, name, total_rows FROM system.tables WHERE database IN ('shop','web','iot') ORDER BY database, name FORMAT PrettyCompactMonoBlock"
CHECK = "http://localhost:8123/?user=student&password=student&query=" + urllib.parse.quote(Q) if False else None


def check_stand():
    import urllib.parse
    url = "http://localhost:8123/?user=student&password=student&query=" + urllib.parse.quote(Q)
    for _ in range(60):
        try:
            out = urllib.request.urlopen(url, timeout=10).read().decode()
            if "10324592" in out and "3174480" in out:
                log("ПРОВЕРКА СТЕНДА ИЗ WINDOWS:\n" + out); return True
        except Exception as e:
            last = e
        time.sleep(10)
    log("стенд не ответил", last if 'last' in dir() else "")


try:
    hide_console()
    sh("wsl --version"); sh("wsl -l -v")
    if MODE == "desktop":
        inst = pathlib.Path("C:/dd/DockerDesktopInstaller.exe"); inst.parent.mkdir(exist_ok=True)
        urllib.request.urlretrieve("https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe", inst)
        sh("Stop-Service docker -Force")
        sh('Start-Process -Wait -FilePath C:/dd/DockerDesktopInstaller.exe -ArgumentList "install","--quiet","--accept-license"')
        subprocess.Popen([r"C:\Program Files\Docker\Docker\Docker Desktop.exe"])
        t0 = time.time(); done = set()
        while time.time() - t0 < 600:
            for w in wins(lambda n: "Docker Desktop" in n):
                txt = " ".join(c.window_text() for c in w.descendants() if c.window_text())
                for key in ("Welcome to Docker", "survey", "Tell us", "role"):
                    if key in txt and key not in done:
                        snap_win("welcome" if key == "Welcome to Docker" else "survey", w)
                        if click_link(w, "Skip") or click_link(w, "Skip survey"):
                            done.add(key)
                if "Engine running" in txt and "engine" not in done:
                    time.sleep(10); snap_win("engine-running", w); done.add("engine")
            for w in wins(lambda n: "Welcome to Windows Subsystem" in n):
                try: w.close()
                except Exception: pass
            if "engine" in done:
                break
            time.sleep(5)
        sh("docker version")
        sh("wsl -l -v")
        sh("git clone https://github.com/MaximBytecamp/clickhouse-practice.git C:/cp")
        sh("cd C:/cp; docker compose up -d 2>&1", timeout=1200)
        check_stand()
        sh("cd C:/cp; docker compose logs seed 2>&1; docker compose ps 2>&1")
        for w in wins(lambda n: "Docker Desktop" in n):
            snap_win("containers", w)
        sh("cd C:/cp; docker compose exec -T clickhouse clickhouse-client -q 'SELECT count() FROM web.events'")
        # диспетчер задач: вкладка производительности
        subprocess.Popen(["taskmgr.exe", "/7", "/startup"]); time.sleep(8)
        for w in wins(lambda n: "Task Manager" in n):
            snap_win("taskmgr", w)
        sh("systeminfo | Select-String 'Hyper-V Requirements' -Context 0,0")
    else:
        sh("wsl --install -d Ubuntu --no-launch")
        sh("wsl -d Ubuntu -u root -- bash -lc 'cat /etc/os-release | head -2; ps -p 1 -o comm='")
        sh("wsl -d Ubuntu -u root -- bash -lc 'curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh 2>&1 | tail -40'", timeout=1500)
        sh("wsl -d Ubuntu -u root -- bash -lc 'systemctl is-active docker; docker version'")
        sh("wsl -d Ubuntu -u root -- bash -lc 'cd ~ && git clone https://github.com/MaximBytecamp/clickhouse-practice.git && cd clickhouse-practice && docker compose up -d 2>&1'", timeout=1500)
        # держим дистрибутив запущенным в фоне, пока проверяем из Windows
        keep = subprocess.Popen(["wsl", "-d", "Ubuntu", "-u", "root", "--", "sleep", "900"])
        check_stand()
        sh("wsl -d Ubuntu -u root -- bash -lc 'cd ~/clickhouse-practice && docker compose logs seed 2>&1 | tail -5; docker compose ps 2>&1'")
        sh("Invoke-WebRequest -UseBasicParsing 'http://localhost:8123/play' | Select-Object StatusCode")
except Exception:
    log(traceback.format_exc()); screen("error")
screen("final")
