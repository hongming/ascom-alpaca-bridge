from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import URLError
from urllib.request import Request, urlopen

import customtkinter as ctk

from ascom_alpaca_bridge.chooser import choose_telescope
from ascom_alpaca_bridge.config import load_config, write_telescope_prog_id


CONFIG_PATH = Path("config.yaml")
APP_TITLE = "ASCOM Alpaca Telescope Bridge"


class BridgeGui(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("560x390")
        self.minsize(520, 360)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.process: subprocess.Popen[str] | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.config_data = load_config(CONFIG_PATH)

        self.status_var = tk.StringVar(value="Stopped")
        self.telescope_var = tk.StringVar(value=self.config_data.telescope.prog_id)
        self.url_var = tk.StringVar(value=self._alpaca_url())
        self.ra_var = tk.StringVar(value="--")
        self.dec_var = tk.StringVar(value="--")

        self._build_ui()
        self.after(250, self._drain_logs)
        self.after(1000, self._poll_status)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        title = ctk.CTkLabel(self, text=APP_TITLE, font=ctk.CTkFont(size=18, weight="bold"))
        title.grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))

        info = ctk.CTkFrame(self)
        info.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        info.grid_columnconfigure(1, weight=1)

        self._info_row(info, 0, "Status", self.status_var)
        self._info_row(info, 1, "Telescope", self.telescope_var)
        self._info_row(info, 2, "Alpaca URL", self.url_var)
        self._info_row(info, 3, "RA", self.ra_var)
        self._info_row(info, 4, "DEC", self.dec_var)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        for column in range(4):
            buttons.grid_columnconfigure(column, weight=1)

        self.choose_button = ctk.CTkButton(buttons, text="Choose", command=self._choose_telescope)
        self.choose_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.start_button = ctk.CTkButton(buttons, text="Start", command=self._start_bridge)
        self.start_button.grid(row=0, column=1, sticky="ew", padx=6)
        self.stop_button = ctk.CTkButton(buttons, text="Stop", command=self._stop_bridge)
        self.stop_button.grid(row=0, column=2, sticky="ew", padx=6)
        self.connect_button = ctk.CTkButton(buttons, text="Connect Scope", command=self._connect_telescope)
        self.connect_button.grid(row=0, column=3, sticky="ew", padx=(6, 0))

        tools = ctk.CTkFrame(self, fg_color="transparent")
        tools.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 12))
        for column in range(3):
            tools.grid_columnconfigure(column, weight=1)
        self.disconnect_button = ctk.CTkButton(tools, text="Disconnect Scope", command=self._disconnect_telescope)
        self.disconnect_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.copy_button = ctk.CTkButton(tools, text="Copy URL", command=self._copy_url)
        self.copy_button.grid(row=0, column=1, sticky="ew", padx=6)
        self.status_button = ctk.CTkButton(tools, text="Open Status", command=self._open_status)
        self.status_button.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        log_label = ctk.CTkLabel(self, text="Log", anchor="w")
        log_label.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 4))

        self.log_box = ctk.CTkTextbox(self, height=120)
        self.log_box.grid(row=5, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.log_box.configure(state="disabled")

    def _info_row(self, parent: ctk.CTkFrame, row: int, label: str, variable: tk.StringVar) -> None:
        label_widget = ctk.CTkLabel(parent, text=label, width=88, anchor="w")
        label_widget.grid(row=row, column=0, sticky="w", padx=(12, 8), pady=6)
        value_widget = ctk.CTkLabel(parent, textvariable=variable, anchor="w")
        value_widget.grid(row=row, column=1, sticky="ew", padx=(0, 12), pady=6)

    def _alpaca_base_url(self) -> str:
        return f"http://127.0.0.1:{self.config_data.server.port}"

    def _alpaca_url(self) -> str:
        return f"{self._alpaca_base_url()}/api/v1/telescope/{self.config_data.telescope.device_number}"

    def _refresh_config(self) -> None:
        self.config_data = load_config(CONFIG_PATH)
        self.telescope_var.set(self.config_data.telescope.prog_id)
        self.url_var.set(self._alpaca_url())

    def _append_log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{timestamp} {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _choose_telescope(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self._append_log("Stop the bridge before choosing a new telescope.")
            return
        try:
            selected = choose_telescope(self.config_data.telescope.prog_id)
        except Exception as exc:
            self._append_log(f"Chooser failed: {exc}")
            return
        if not selected:
            self._append_log("Chooser cancelled.")
            return
        write_telescope_prog_id(CONFIG_PATH, selected)
        self._refresh_config()
        self._append_log(f"Selected telescope: {selected}")

    def _start_bridge(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self._append_log("Bridge is already running.")
            return
        self._refresh_config()
        command = [sys.executable, "run_bridge.py", "--config", str(CONFIG_PATH)]
        creationflags = 0
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creationflags,
            )
        except Exception as exc:
            self._append_log(f"Start failed: {exc}")
            self.status_var.set("Error")
            return
        self.status_var.set("Starting")
        self._append_log("Bridge process started.")
        threading.Thread(target=self._read_process_output, daemon=True).start()

    def _read_process_output(self) -> None:
        if self.process is None or self.process.stdout is None:
            return
        for line in self.process.stdout:
            self.log_queue.put(line.rstrip())

    def _stop_bridge(self) -> None:
        if self.process is None or self.process.poll() is not None:
            self.status_var.set("Stopped")
            self._append_log("Bridge is not running.")
            return
        self._append_log("Stopping bridge...")
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._append_log("Force killing bridge.")
            self.process.kill()
        self.status_var.set("Stopped")

    def _copy_url(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self._alpaca_url())
        self._append_log("Alpaca URL copied.")

    def _open_status(self) -> None:
        webbrowser.open(f"{self._alpaca_base_url()}/status")

    def _read_telescope_value(self, member: str, timeout: float = 0.5) -> object | None:
        try:
            with urlopen(f"{self._alpaca_url()}/{member}", timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None
        if payload.get("ErrorNumber") != 0:
            return None
        return payload.get("Value")

    def _update_coordinates(self, connected: object) -> None:
        if connected is not True:
            self.ra_var.set("--")
            self.dec_var.set("--")
            return
        ra = self._read_telescope_value("rightascension")
        dec = self._read_telescope_value("declination")
        if isinstance(ra, (int, float)):
            self.ra_var.set(f"{ra:.4f} h")
        else:
            self.ra_var.set("--")
        if isinstance(dec, (int, float)):
            self.dec_var.set(f"{dec:.4f} deg")
        else:
            self.dec_var.set("--")

    def _set_telescope_connected(self, connected: bool) -> None:
        if self.process is None or self.process.poll() is not None:
            self._append_log("Start the bridge before connecting the telescope.")
            return
        label = "true" if connected else "false"
        endpoint = f"{self._alpaca_url()}/connected"
        data = urlencode({"Connected": label, "ClientTransactionID": "1"}).encode("utf-8")
        request = Request(
            endpoint,
            data=data,
            method="PUT",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            self.log_queue.put(f"Telescope connection request failed: {exc}")
            return
        if payload.get("ErrorNumber") == 0:
            action = "connected" if connected else "disconnected"
            self.log_queue.put(f"Telescope {action}.")
        else:
            self.log_queue.put(f"Telescope connection error: {payload.get('ErrorMessage')}")

    def _connect_telescope(self) -> None:
        threading.Thread(target=self._set_telescope_connected, args=(True,), daemon=True).start()

    def _disconnect_telescope(self) -> None:
        threading.Thread(target=self._set_telescope_connected, args=(False,), daemon=True).start()

    def _drain_logs(self) -> None:
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if line:
                self._append_log(line)
        self.after(250, self._drain_logs)

    def _poll_status(self) -> None:
        if self.process is not None and self.process.poll() is not None:
            self.status_var.set("Stopped")
        elif self.process is not None:
            try:
                with urlopen(f"{self._alpaca_base_url()}/status", timeout=0.5) as response:
                    data = json.loads(response.read().decode("utf-8"))
                connected = data.get("telescope", {}).get("connected")
                state = "Running"
                if connected is True:
                    state = "Running, Telescope Connected"
                elif connected is False:
                    state = "Running, Telescope Disconnected"
                self.status_var.set(state)
                self._update_coordinates(connected)
            except (OSError, URLError, TimeoutError, json.JSONDecodeError):
                self.status_var.set("Starting")
                self._update_coordinates(False)
        self.after(1000, self._poll_status)

    def _on_close(self) -> None:
        self._stop_bridge()
        self.destroy()


def main() -> None:
    app = BridgeGui()
    app.mainloop()


if __name__ == "__main__":
    main()
