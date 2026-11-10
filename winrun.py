"""Разведка: установка и первый запуск Docker Desktop на Windows (GitHub Actions).

Скрипт запускает установщик с окнами, раз в несколько секунд снимает экран,
пишет в журнал видимые окна с их кнопками и сам нажимает кнопку, которая
ведёт дальше. Снимок сохраняется, только когда меняется набор окон и текстов."""
import pathlib, subprocess, time, urllib.request, traceback
from PIL import ImageGrab
from pywinauto import Desktop

OUT = pathlib.Path("shots-out").resolve(); OUT.mkdir(exist_ok=True)
LOG = open(OUT / "log.txt", "a", encoding="utf-8")
N = [0]
NEXT = ["OK", "Ok", "Close", "Accept", "Close and restart", "Continue", "Skip", "Finish", "Next"]


def log(*a):
    t = " ".join(str(x) for x in a); print(t, flush=True); LOG.write(t + "\n"); LOG.flush()


def ours(name):
    return "Docker" in name or "WSL" in name or "Windows Subsystem" in name


def state():
    rows = []
    for w in Desktop(backend="uia").windows():
        try:
            if not w.is_visible() or not w.window_text():
                continue
            name = w.window_text()
            if not ours(name):
                continue
            items = []
            for c in w.descendants():
                try:
                    if c.element_info.control_type in ("Button", "Text", "CheckBox", "Hyperlink") and c.window_text():
                        items.append(f"{c.element_info.control_type}:{c.window_text()[:80]}")
                except Exception:
                    pass
            rows.append((name, tuple(items[:60]), w))
        except Exception:
            pass
    return rows


def snap(tag, rows):
    N[0] += 1
    name = f"{N[0]:02d}-{tag}.png"
    ImageGrab.grab(all_screens=True).save(OUT / name)
    log("СНИМОК", name)
    for k, (title, items, w) in enumerate(rows):
        try:
            r = w.rectangle(); log("  окно", repr(title), (r.left, r.top, r.right, r.bottom))
            ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom), all_screens=True).save(OUT / f"{N[0]:02d}-{tag}-win{k}.png")
        except Exception:
            log("  окно", repr(title))
        for i in items:
            log("     ", i)


def watch(tag, seconds, click=True, stop=None):
    last, t0 = None, time.time()
    while time.time() - t0 < seconds:
        rows = state()
        key = tuple((t, i) for t, i, _ in rows)
        if key != last:
            snap(tag, rows); last = key
        if stop and stop(rows):
            return
        if click:
            for title, items, w in rows:
                for label in NEXT:
                    if f"Button:{label}" in items:
                        try:
                            time.sleep(1.5); snap(tag + "-before-" + label.replace(" ", "_"), state())
                            # кнопки заголовка окна (крестик, свернуть) не трогаем: только ниже полосы заголовка
                            top = w.rectangle().top + 60
                            btn = next(c for c in w.descendants(control_type="Button")
                                       if c.window_text() == label and c.rectangle().top > top)
                            btn.click_input()
                            log("НАЖАТО", label, "в", repr(title)); time.sleep(3)
                        except Exception as e:
                            log("не нажалось", label, e)
                        break
        time.sleep(4)


def hide_console():
    for w in Desktop(backend="win32").windows():
        try:
            if "hosted-compute-agent" in w.window_text():
                w.minimize(); log("свернул консоль агента")
        except Exception:
            pass


try:
    hide_console()
    log(subprocess.run(["powershell", "-c", "Get-ComputerInfo -Property OsName,OsVersion,CsProcessors | Format-List; wsl --status"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stdout)
    inst = pathlib.Path("C:/dd/DockerDesktopInstaller.exe"); inst.parent.mkdir(exist_ok=True)
    log("скачиваю установщик")
    urllib.request.urlretrieve("https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe", inst)
    log("размер", inst.stat().st_size)
    hide_console()
    p = subprocess.Popen([str(inst)])
    watch("install", 900, stop=lambda rows: p.poll() is not None and not rows)
    log("установщик завершился с кодом", p.poll())
    exe = pathlib.Path("C:/Program Files/Docker/Docker/Docker Desktop.exe")
    log("Docker Desktop.exe есть:", exe.exists())
    if exe.exists():
        hide_console()
        subprocess.Popen([str(exe)])
        watch("first-run", 420)
    snap("final", state())
except Exception:
    log(traceback.format_exc())
    ImageGrab.grab(all_screens=True).save(OUT / "error.png")
