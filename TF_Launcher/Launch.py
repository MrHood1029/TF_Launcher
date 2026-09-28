"""
КИБЕРТРОН // ЛАУНЧЕР
Под управлением Сентинела Прайма.
Единый каркас для РП-сервера.
"""

import customtkinter as ctk
import minecraft_launcher_lib
import subprocess
import os
import json
import sys
import threading
import requests
import hashlib
import uuid
from packaging import version as pkg_version
from tkinter import filedialog, messagebox

# ============================================================
# КОНСТАНТЫ
# ============================================================

LAUNCHER_VERSION = "1.0.0"
CONFIG_FILE = "launcher_config.json"
ACCOUNTS_FILE = "cybertron_accounts.json"
SERVER_BASE_URL = "https://launcher.cybertron-rp.ru"
YGGDRASIL_URL = "https://auth.cybertron-rp.ru"

ADMIN_PASSWORD = "1234"

# Папка Minecraft рядом с лаунчером — чтобы не слетала при передаче
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MC_DIR = os.path.join(BASE_DIR, "Minecraft")

DEFAULT_CONFIG = {
    "ram": "4G",
    "java_path": "",
    "username": "",
    "password": "",
    "minecraft_dir": DEFAULT_MC_DIR,
    "server_ip": "play.cybertron-rp.ru",
    "version": "1.20.1-forge-47.2.0",
    "theme": "matrix_gold",
    "epoch_name": "Золотой век",
    "admin_mode": False
}

THEMES = {
    "matrix_gold": {"name": "Матрица (Золото)", "bg": "#0a0a0c", "fg": "#d4af37", "panel": "#141418", "text": "#8a8a8a", "accent": "#b22222", "button_text": "#0a0a0c"},
    "dark_energon": {"name": "Тёмный Энергон", "bg": "#0d0d1a", "fg": "#8a2be2", "panel": "#1a1a2e", "text": "#6a6a8a", "accent": "#ff4500", "button_text": "#ffffff"},
    "crystal_city": {"name": "Хрустальный Город", "bg": "#e8e8f0", "fg": "#1a1a2e", "panel": "#ffffff", "text": "#4a4a5a", "accent": "#c0c0d0", "button_text": "#ffffff"},
    "rust_sea": {"name": "Море Ржавчины", "bg": "#1a0f0a", "fg": "#b87333", "panel": "#2a1a10", "text": "#8a6a5a", "accent": "#ff6347", "button_text": "#1a0f0a"},
    "sentinel_prime": {"name": "Сентинел Прайм", "bg": "#0f1420", "fg": "#4a90d9", "panel": "#1a2233", "text": "#7a8aa0", "accent": "#d4af37", "button_text": "#ffffff"},
    "decepticon": {"name": "Десептикон", "bg": "#1a0a0a", "fg": "#8b0000", "panel": "#2a1010", "text": "#8a5a5a", "accent": "#4a0000", "button_text": "#ffffff"},
    "autobot": {"name": "Автобот", "bg": "#0a1a2a", "fg": "#c0c0c0", "panel": "#102030", "text": "#7a8a9a", "accent": "#ff0000", "button_text": "#0a1a2a"},
    "unicron": {"name": "Юникрон", "bg": "#0a0a0a", "fg": "#8b00ff", "panel": "#1a0a1a", "text": "#6a4a6a", "accent": "#ff00ff", "button_text": "#ffffff"}
}

# ============================================================
# РАБОТА С КОНФИГОМ И АККАУНТАМИ
# ============================================================

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ============================================================
# РЕГИСТРАЦИЯ И ВХОД
# ============================================================

def register_player(nick, password):
    accounts = load_accounts()
    if nick in accounts:
        return False, "Игрок с таким ником уже существует."
    pwd_hash = hash_password(password)
    accounts[nick] = {"password": pwd_hash, "uuid": str(uuid.uuid4())}
    save_accounts(accounts)
    try:
        requests.post(f"{SERVER_BASE_URL}/api/register", json={"nick": nick, "password": pwd_hash}, timeout=5)
    except Exception:
        pass
    return True, "Регистрация успешна."

def login_player(nick, password):
    accounts = load_accounts()
    if nick not in accounts:
        return False, "Игрок не найден. Зарегистрируйтесь."
    pwd_hash = hash_password(password)
    if accounts[nick]["password"] != pwd_hash:
        return False, "Неверный пароль."
    return True, accounts[nick]["uuid"]

# ============================================================
# АВТООБНОВЛЕНИЕ ЛАУНЧЕРА
# ============================================================

def check_launcher_update():
    try:
        r = requests.get(f"{SERVER_BASE_URL}/launcher/version.txt", timeout=5)
        remote = r.text.strip()
        if pkg_version.parse(remote) > pkg_version.parse(LAUNCHER_VERSION):
            return remote
    except Exception:
        pass
    return None

def download_update(remote_version):
    try:
        url = f"{SERVER_BASE_URL}/launcher/CybertronLauncher.exe"
        r = requests.get(url, stream=True, timeout=30)
        temp_path = os.path.join(os.environ.get("TEMP", "."), "CybertronLauncher_new.exe")
        with open(temp_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        subprocess.Popen([temp_path])
        sys.exit(0)
    except Exception as e:
        messagebox.showerror("Ошибка обновления", str(e))

# ============================================================
# YGGDRASIL АВТОРИЗАЦИЯ
# ============================================================

def yggdrasil_authenticate(username, password):
    try:
        r = requests.post(
            f"{YGGDRASIL_URL}/authserver/authenticate",
            json={"username": username, "password": password, "clientToken": "cybertron-launcher", "requestUser": True},
            timeout=10
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

# ============================================================
# СБОРКА (MANIFEST)
# ============================================================

def fetch_manifest():
    try:
        r = requests.get(f"{SERVER_BASE_URL}/modpack/manifest.json", timeout=10)
        return r.json()
    except Exception:
        return None

def download_mods(manifest, callback):
    mods_dir = os.path.join(load_config()["minecraft_dir"], "mods")
    os.makedirs(mods_dir, exist_ok=True)
    mods = manifest.get("mods", [])
    total = len(mods)
    for i, mod in enumerate(mods):
        mod_path = os.path.join(mods_dir, mod["name"])
        if not os.path.exists(mod_path):
            try:
                r = requests.get(mod["url"], stream=True, timeout=30)
                with open(mod_path, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
            except Exception:
                pass
        if callback:
            callback["setStatus"](f"Загрузка модов: {i+1}/{total}")
            callback["setProgress"](i + 1)
            callback["setMax"](total)

# ============================================================
# ЗАГРУЗКА ВЕРСИИ MINECRAFT (КЛЮЧЕВАЯ ФУНКЦИЯ)
# ============================================================

def ensure_version_installed(version_id, minecraft_dir, callback=None, java_path=None):
    """Проверяет и устанавливает версию, если её нет."""
    installed = minecraft_launcher_lib.utils.get_installed_versions(minecraft_dir)
    if any(v["id"] == version_id for v in installed):
        if callback:
            callback["setStatus"](f"Версия {version_id} уже установлена.")
        return True

    if "forge" in version_id.lower():
        try:
            if callback:
                callback["setStatus"](f"Установка Forge {version_id}...")
            # Передаём путь к Java, если он указан
            minecraft_launcher_lib.forge.install_forge_version(
                version_id, minecraft_dir, callback=callback, java=java_path
            )
            return True
        except Exception as e:
            if callback:
                callback["setStatus"](f"Ошибка Forge: {e}")
            return False
    else:
        try:
            if callback:
                callback["setStatus"](f"Установка Minecraft {version_id}...")
            minecraft_launcher_lib.install.install_minecraft_version(
                version_id, minecraft_dir, callback=callback
            )
            return True
        except Exception as e:
            if callback:
                callback["setStatus"](f"Ошибка установки: {e}")
            return False

# ============================================================
# ГЛАВНОЕ ОКНО ЛАУНЧЕРА
# ============================================================

class CybertronLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config_data = load_config()
        self.theme = THEMES.get(self.config_data["theme"], THEMES["matrix_gold"])
        self.auth_data = None
        self.title("КИБЕРТРОН // ЛАУНЧЕР")
        self.geometry("900x720")
        self.resizable(False, False)
        self._apply_theme()
        self._build_ui()
        self.after(500, self._check_updates_async)
        self.after(1000, self._fetch_epoch_async)
        self.after(1500, self._check_first_run)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_theme(self):
        ctk.set_appearance_mode("dark" if self.theme["bg"] < "#888888" else "light")
        self.configure(fg_color=self.theme["bg"])

    def _rebuild_ui(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.theme = THEMES.get(self.config_data["theme"], THEMES["matrix_gold"])
        self._apply_theme()
        self._build_ui()

    def _build_ui(self):
        t = self.theme
        self.main = ctk.CTkFrame(self, fg_color=t["bg"], corner_radius=0)
        self.main.pack(fill="both", expand=True, padx=20, pady=20)

        self.title_label = ctk.CTkLabel(self.main, text="КИБЕРТРОН", font=("Arial", 42, "bold"), text_color=t["fg"])
        self.title_label.pack(pady=(20, 0))

        self.epoch_label = ctk.CTkLabel(self.main, text=self.config_data.get("epoch_name", "ЗОЛОТОЙ ВЕК").upper(), font=("Arial", 14), text_color=t["text"])
        self.epoch_label.pack(pady=(0, 20))

        self.status_label = ctk.CTkLabel(self.main, text="Система готова.", font=("Arial", 13), text_color=t["text"])
        self.status_label.pack(pady=(0, 10))

        self.progress = ctk.CTkProgressBar(self.main, width=500, progress_color=t["fg"])
        self.progress.set(0)
        self.progress.pack(pady=(0, 15))

        self.play_btn = ctk.CTkButton(self.main, text="ЗАПУСТИТЬ КИБЕРТРОН", font=("Arial", 18, "bold"), fg_color=t["fg"], hover_color=t["accent"], text_color=t["button_text"], corner_radius=8, width=320, height=55, command=self._on_play)
        self.play_btn.pack(pady=10)

        bottom = ctk.CTkFrame(self.main, fg_color=t["panel"], corner_radius=8)
        bottom.pack(fill="x", side="bottom", padx=20, pady=20)

        btn_row = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_row.pack(pady=15)

        ctk.CTkButton(btn_row, text="⚙ НАСТРОЙКИ", width=160, height=38, fg_color=t["panel"], hover_color=t["accent"], text_color=t["fg"], border_width=1, border_color=t["fg"], command=self._open_settings).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="🎨 ТЕМА", width=120, height=38, fg_color=t["panel"], hover_color=t["accent"], text_color=t["fg"], border_width=1, border_color=t["fg"], command=self._open_theme_picker).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="👤 АККАУНТ", width=120, height=38, fg_color=t["panel"], hover_color=t["accent"], text_color=t["fg"], border_width=1, border_color=t["fg"], command=self._open_account).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="🛡 АДМИН", width=120, height=38, fg_color=t["panel"], hover_color=t["accent"], text_color=t["fg"], border_width=1, border_color=t["fg"], command=self._open_admin).pack(side="left", padx=5)

        self.info_label = ctk.CTkLabel(bottom, text=f"Версия лаунчера: {LAUNCHER_VERSION}  |  Сервер: {self.config_data['server_ip']}", font=("Arial", 10), text_color=t["text"])
        self.info_label.pack(pady=(0, 10))

    def _set_status(self, text):
        self.status_label.configure(text=text)
        self.update()

    def _set_progress(self, value, maximum):
        if maximum > 0:
            self.progress.set(value / maximum)
        self.update()

    def _install_callback(self):
        def set_status(text): self._set_status(text)
        def set_progress(value): self._set_progress(value, 100)
        def set_max(m): pass
        return {"setStatus": set_status, "setProgress": set_progress, "setMax": set_max}

    def _on_play(self):
        self.play_btn.configure(state="disabled", text="ЗАГРУЗКА...")
        threading.Thread(target=self._launch_thread, daemon=True).start()

    def _launch_thread(self):
        try:
            cfg = self.config_data
            if not cfg["username"]:
                self._set_status("Сначала зарегистрируйтесь или войдите.")
                self.play_btn.configure(state="normal", text="ЗАПУСТИТЬ КИБЕРТРОН")
                return

            ok, msg = login_player(cfg["username"], cfg["password"])
            if not ok:
                self._set_status(f"Ошибка входа: {msg}")
                self.play_btn.configure(state="normal", text="ЗАПУСТИТЬ КИБЕРТРОН")
                return

            self._set_status("Авторизация на сервере...")
            self.auth_data = yggdrasil_authenticate(cfg["username"], cfg["password"])
            if not self.auth_data:
                accounts = load_accounts()
                local_uuid = accounts.get(cfg["username"], {}).get("uuid", str(uuid.uuid4()))
                self.auth_data = {"selectedProfile": {"name": cfg["username"], "id": local_uuid}, "accessToken": "offline_token"}

            self._set_status("Загрузка манифеста сборки...")
            manifest = fetch_manifest()
            if manifest:
                download_mods(manifest, self._install_callback())
                forge_version = manifest.get("forge_version", cfg["version"])
            else:
                forge_version = cfg["version"]

            # Ключевой момент: передаём java_path в установку
            self._set_status(f"Проверка версии {forge_version}...")
            if not ensure_version_installed(forge_version, cfg["minecraft_dir"], self._install_callback(), cfg.get("java_path")):
                self._set_status("Не удалось установить версию.")
                self.play_btn.configure(state="normal", text="ПОВТОРИТЬ ЗАПУСК")
                return

            self._set_status("ЗАПУСК КИБЕРТРОНА...")
            profile = self.auth_data["selectedProfile"]
            options = {
                "username": profile["name"],
                "uuid": profile["id"],
                "token": self.auth_data["accessToken"],
                "server": cfg["server_ip"],
                "port": "25565",
                "launcherName": "CybertronLauncher",
                "launcherVersion": LAUNCHER_VERSION,
                "jvmArguments": [f"-Xmx{cfg['ram']}", f"-Xms{cfg['ram']}", f"-javaagent:authlib-injector.jar={YGGDRASIL_URL}"]
            }
            # Если указан путь к Java — используем его принудительно
            if cfg.get("java_path"):
                options["executablePath"] = cfg["java_path"]

            command = minecraft_launcher_lib.command.get_minecraft_command(forge_version, cfg["minecraft_dir"], options)
            subprocess.run(command, cwd=cfg["minecraft_dir"])
            self._set_status("Сессия завершена. Кибертрон ждёт.")
            self.play_btn.configure(state="normal", text="ЗАПУСТИТЬ КИБЕРТРОН")

        except Exception as e:
            self._set_status(f"ОШИБКА: {str(e)}")
            self.play_btn.configure(state="normal", text="ПОВТОРИТЬ ЗАПУСК")

    # ---------- НАСТРОЙКИ (общие) ----------
    def _open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Настройки")
        win.geometry("500x500")
        win.configure(fg_color=self.theme["bg"])
        win.grab_set()

        ctk.CTkLabel(win, text="НАСТРОЙКИ", font=("Arial", 22, "bold"), text_color=self.theme["fg"]).pack(pady=20)
        frame = ctk.CTkFrame(win, fg_color=self.theme["panel"])
        frame.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(frame, text="Ник:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(15, 0))
        nick = ctk.CTkEntry(frame, width=400)
        nick.insert(0, self.config_data["username"])
        nick.pack(padx=15, pady=5)

        ctk.CTkLabel(frame, text="Пароль:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(10, 0))
        pwd = ctk.CTkEntry(frame, width=400, show="*")
        pwd.insert(0, self.config_data["password"])
        pwd.pack(padx=15, pady=5)

        ctk.CTkLabel(frame, text="ОЗУ:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(10, 0))
        ram = ctk.CTkOptionMenu(frame, values=["2G", "4G", "6G", "8G", "12G", "16G"], width=400)
        ram.set(self.config_data["ram"])
        ram.pack(padx=15, pady=5)

        ctk.CTkLabel(frame, text="Путь к Java:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(10, 0))
        java_row = ctk.CTkFrame(frame, fg_color="transparent")
        java_row.pack(fill="x", padx=15, pady=5)
        java_entry = ctk.CTkEntry(java_row, width=300)
        java_entry.insert(0, self.config_data.get("java_path", ""))
        java_entry.pack(side="left", padx=(0, 5))
        ctk.CTkButton(java_row, text="Обзор", width=90, command=lambda: java_entry.delete(0, "end") or java_entry.insert(0, filedialog.askopenfilename())).pack(side="left")

        ctk.CTkLabel(frame, text="Папка Minecraft:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(10, 0))
        mc_row = ctk.CTkFrame(frame, fg_color="transparent")
        mc_row.pack(fill="x", padx=15, pady=5)
        mc_entry = ctk.CTkEntry(mc_row, width=300)
        mc_entry.insert(0, self.config_data["minecraft_dir"])
        mc_entry.pack(side="left", padx=(0, 5))
        ctk.CTkButton(mc_row, text="Обзор", width=90, command=lambda: mc_entry.delete(0, "end") or mc_entry.insert(0, filedialog.askdirectory())).pack(side="left")

        def save():
            self.config_data.update({
                "username": nick.get(),
                "password": pwd.get(),
                "ram": ram.get(),
                "java_path": java_entry.get(),
                "minecraft_dir": mc_entry.get()
            })
            save_config(self.config_data)
            self._set_status("Настройки сохранены.")
            win.destroy()

        ctk.CTkButton(win, text="СОХРАНИТЬ", fg_color=self.theme["fg"], text_color=self.theme["button_text"], command=save).pack(pady=15)

    # ---------- ВЫБОР ТЕМЫ ----------
    def _open_theme_picker(self):
        win = ctk.CTkToplevel(self)
        win.title("Тема")
        win.geometry("450x600")
        win.configure(fg_color=self.theme["bg"])
        win.grab_set()

        ctk.CTkLabel(win, text="ВЫБЕРИТЕ ТЕМУ", font=("Arial", 20, "bold"), text_color=self.theme["fg"]).pack(pady=20)

        def pick(key):
            self.config_data["theme"] = key
            save_config(self.config_data)
            win.destroy()
            self._rebuild_ui()

        for key, theme in THEMES.items():
            ctk.CTkButton(win, text=theme["name"], width=320, height=40, fg_color=theme["fg"], hover_color=theme["accent"], text_color=theme["button_text"], command=lambda k=key: pick(k)).pack(pady=5)

    # ---------- АККАУНТ ----------
    def _open_account(self):
        win = ctk.CTkToplevel(self)
        win.title("Аккаунт")
        win.geometry("450x500")
        win.configure(fg_color=self.theme["bg"])
        win.grab_set()

        ctk.CTkLabel(win, text="АККАУНТ", font=("Arial", 22, "bold"), text_color=self.theme["fg"]).pack(pady=20)

        tabview = ctk.CTkTabview(win, fg_color=self.theme["panel"])
        tabview.pack(fill="both", expand=True, padx=20, pady=10)

        tab_login = tabview.add("Вход")
        tab_register = tabview.add("Регистрация")

        ctk.CTkLabel(tab_login, text="Ник:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(15, 0))
        login_nick = ctk.CTkEntry(tab_login, width=350)
        login_nick.pack(padx=15, pady=5)
        ctk.CTkLabel(tab_login, text="Пароль:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(10, 0))
        login_pwd = ctk.CTkEntry(tab_login, width=350, show="*")
        login_pwd.pack(padx=15, pady=5)

        def do_login():
            ok, msg = login_player(login_nick.get(), login_pwd.get())
            if ok:
                self.config_data["username"] = login_nick.get()
                self.config_data["password"] = login_pwd.get()
                save_config(self.config_data)
                self._set_status(f"Вошли как {login_nick.get()}")
                win.destroy()
            else:
                messagebox.showerror("Ошибка входа", msg)

        ctk.CTkButton(tab_login, text="ВОЙТИ", fg_color=self.theme["fg"], text_color=self.theme["button_text"], command=do_login).pack(pady=20)

        ctk.CTkLabel(tab_register, text="Ник:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(15, 0))
        reg_nick = ctk.CTkEntry(tab_register, width=350)
        reg_nick.pack(padx=15, pady=5)
        ctk.CTkLabel(tab_register, text="Пароль:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(10, 0))
        reg_pwd = ctk.CTkEntry(tab_register, width=350, show="*")
        reg_pwd.pack(padx=15, pady=5)
        ctk.CTkLabel(tab_register, text="Повторите пароль:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(10, 0))
        reg_pwd2 = ctk.CTkEntry(tab_register, width=350, show="*")
        reg_pwd2.pack(padx=15, pady=5)

        def do_register():
            if reg_pwd.get() != reg_pwd2.get():
                messagebox.showerror("Ошибка", "Пароли не совпадают.")
                return
            if not reg_nick.get() or not reg_pwd.get():
                messagebox.showerror("Ошибка", "Заполните все поля.")
                return
            ok, msg = register_player(reg_nick.get(), reg_pwd.get())
            if ok:
                self.config_data["username"] = reg_nick.get()
                self.config_data["password"] = reg_pwd.get()
                save_config(self.config_data)
                self._set_status(f"Зарегистрирован как {reg_nick.get()}")
                win.destroy()
            else:
                messagebox.showerror("Ошибка регистрации", msg)

        ctk.CTkButton(tab_register, text="ЗАРЕГИСТРИРОВАТЬСЯ", fg_color=self.theme["fg"], text_color=self.theme["button_text"], command=do_register).pack(pady=20)

    # ---------- АДМИН-ПАНЕЛЬ (ОБНОВЛЁННАЯ) ----------
    def _open_admin(self):
        win = ctk.CTkToplevel(self)
        win.title("Админ-панель")
        win.geometry("650x650")
        win.configure(fg_color=self.theme["bg"])
        win.grab_set()

        ctk.CTkLabel(win, text="АДМИН-ПАНЕЛЬ", font=("Arial", 22, "bold"), text_color=self.theme["fg"]).pack(pady=15)

        pwd_frame = ctk.CTkFrame(win, fg_color=self.theme["panel"])
        pwd_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(pwd_frame, text="Пароль админа:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(10, 0))
        pwd = ctk.CTkEntry(pwd_frame, width=400, show="*")
        pwd.pack(padx=15, pady=10)

        content = ctk.CTkFrame(win, fg_color=self.theme["panel"])

        def unlock():
            if pwd.get() != ADMIN_PASSWORD:
                messagebox.showerror("Ошибка", "Неверный пароль.")
                return
            pwd_frame.pack_forget()
            content.pack(fill="both", expand=True, padx=20, pady=10)
            build_content()

        ctk.CTkButton(pwd_frame, text="ВОЙТИ", fg_color=self.theme["fg"], text_color=self.theme["button_text"], command=unlock).pack(pady=10)

        def build_content():
            # IP сервера
            ctk.CTkLabel(content, text="IP сервера:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(15, 0))
            ip_entry = ctk.CTkEntry(content, width=450)
            ip_entry.insert(0, self.config_data["server_ip"])
            ip_entry.pack(padx=15, pady=5)

            # Название эпохи
            ctk.CTkLabel(content, text="Название эпохи:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(10, 0))
            epoch_entry = ctk.CTkEntry(content, width=450)
            epoch_entry.insert(0, self.config_data["epoch_name"])
            epoch_entry.pack(padx=15, pady=5)

            # Версия сборки (Forge/ваниль)
            ctk.CTkLabel(content, text="Версия сборки (Forge или ваниль):", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(10, 0))
            ver_entry = ctk.CTkEntry(content, width=450)
            ver_entry.insert(0, self.config_data["version"])
            ver_entry.pack(padx=15, pady=5)

            # Путь к Java
            ctk.CTkLabel(content, text="Путь к Java (для сборки):", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(10, 0))
            java_row = ctk.CTkFrame(content, fg_color="transparent")
            java_row.pack(fill="x", padx=15, pady=5)
            java_entry = ctk.CTkEntry(java_row, width=300)
            java_entry.insert(0, self.config_data.get("java_path", ""))
            java_entry.pack(side="left", padx=(0, 5))
            ctk.CTkButton(java_row, text="Обзор", width=90, command=lambda: java_entry.delete(0, "end") or java_entry.insert(0, filedialog.askopenfilename())).pack(side="left")

            # Кнопка установки сборки
            def install_build():
                version = ver_entry.get()
                mc_dir = self.config_data["minecraft_dir"]
                java = java_entry.get() or None
                self._set_status(f"Установка {version}...")
                def run():
                    ok = ensure_version_installed(version, mc_dir, self._install_callback(), java)
                    if ok:
                        self._set_status(f"Версия {version} установлена.")
                        messagebox.showinfo("Успех", f"Версия {version} готова.")
                    else:
                        self._set_status("Ошибка установки.")
                        messagebox.showerror("Ошибка", "Не удалось установить версию.")
                threading.Thread(target=run, daemon=True).start()

            ctk.CTkButton(content, text="📥 УСТАНОВИТЬ СБОРКУ", fg_color=self.theme["accent"], text_color=self.theme["button_text"], command=install_build).pack(pady=10)

            # Загрузка манифеста
            ctk.CTkLabel(content, text="Загрузить manifest.json:", text_color=self.theme["text"]).pack(anchor="w", padx=15, pady=(10, 0))
            manifest_path = ctk.CTkEntry(content, width=350, placeholder_text="Путь к manifest.json")
            manifest_path.pack(padx=15, pady=5)

            def upload_manifest():
                path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
                if path:
                    manifest_path.delete(0, "end")
                    manifest_path.insert(0, path)

            ctk.CTkButton(content, text="Выбрать файл", command=upload_manifest).pack(pady=5)

            # Отправка на сервер
            def send_to_server():
                data = {
                    "server_ip": ip_entry.get(),
                    "epoch_name": epoch_entry.get(),
                    "version": ver_entry.get(),
                    "java_path": java_entry.get()
                }
                try:
                    r = requests.post(f"{SERVER_BASE_URL}/api/config", json=data, timeout=10)
                    if r.status_code == 200:
                        self.config_data.update(data)
                        save_config(self.config_data)
                        self.epoch_label.configure(text=data["epoch_name"].upper())
                        messagebox.showinfo("Успех", "Конфиг отправлен на сервер.")
                    else:
                        messagebox.showerror("Ошибка", f"Сервер вернул {r.status_code}")
                except Exception as e:
                    messagebox.showerror("Ошибка", str(e))

            ctk.CTkButton(content, text="ОТПРАВИТЬ НА СЕРВЕР", fg_color=self.theme["fg"], text_color=self.theme["button_text"], command=send_to_server).pack(pady=15)

        win.bind("<Return>", lambda e: unlock())

    # ---------- АСИНХРОННЫЕ ПРОВЕРКИ ----------
    def _check_updates_async(self):
        def run():
            remote = check_launcher_update()
            if remote:
                if messagebox.askyesno("Обновление", f"Доступна версия {remote}. Скачать?"):
                    download_update(remote)
        threading.Thread(target=run, daemon=True).start()

    def _fetch_epoch_async(self):
        def run():
            try:
                r = requests.get(f"{SERVER_BASE_URL}/server_config.json", timeout=5)
                data = r.json()
                if "epoch_name" in data:
                    self.config_data["epoch_name"] = data["epoch_name"]
                    self.epoch_label.configure(text=data["epoch_name"].upper())
                    save_config(self.config_data)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def _check_first_run(self):
        if not self.config_data.get("username"):
            self._open_account()

    def _on_close(self):
        save_config(self.config_data)
        self.destroy()

if __name__ == "__main__":
    app = CybertronLauncher()
    app.mainloop()