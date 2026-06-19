from __future__ import annotations

import argparse
import json
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import webbrowser

import customtkinter as ctk

from ascom_alpaca_bridge.chooser import choose_camera, choose_dome, choose_focuser, choose_telescope
from ascom_alpaca_bridge.config import (
    load_config,
    write_camera_prog_id,
    write_dome_prog_id,
    write_focuser_prog_id,
    write_telescope_prog_id,
)


APP_TITLE = "ASCOM Alpaca Bridge"
DEVICE_TYPES = ("telescope", "dome", "focuser", "camera")
DEVICE_LABELS = {
    "telescope": "Telescope",
    "dome": "Dome",
    "focuser": "Focuser",
    "camera": "Camera",
}
COLORS = {
    "bg": "#F5F7FB",
    "panel": "#FFFFFF",
    "panel_alt": "#F8FAFC",
    "line": "#DDE5F0",
    "line_soft": "#E6ECF4",
    "text": "#1F2937",
    "white": "#FFFFFF",
    "muted": "#64748B",
    "weak": "#94A3B8",
    "success": "#059669",
    "blue": "#2563EB",
    "blue_hover": "#1D4ED8",
    "orange": "#F97316",
    "orange_hover": "#EA580C",
    "gray": "#64748B",
    "gray_hover": "#475569",
    "disabled": "#E2E8F0",
    "button": "#FFFFFF",
    "button_hover": "#F1F5F9",
    "row_alt": "#F8FAFC",
    "red": "#DC2626",
    "red_soft": "#FEF2F2",
    "red_hover": "#FEE2E2",
    "amber": "#D97706",
}
STATUS_COLORS = {
    "Connected": COLORS["success"],
    "Disconnected": COLORS["muted"],
    "Disabled": COLORS["weak"],
    "Error": COLORS["red"],
    "Unknown": COLORS["amber"],
    "Busy": COLORS["amber"],
}


class SimpleBridgeGui(ctk.CTk):
    def __init__(self, config_path: str | Path = "config.yaml") -> None:
        super().__init__()
        self.config_path = Path(config_path)
        self.title(APP_TITLE)
        self.geometry("780x430")
        self.minsize(700, 400)
        self.configure(fg_color=COLORS["bg"])

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.process: subprocess.Popen[str] | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.config_data = load_config(self.config_path)
        self.last_status: dict[str, object] | None = None
        self.bridge_reachable = False
        self.status_failures = 0

        self.bridge_var = tk.StringVar(value="Bridge: Stopped")
        self.url_var = tk.StringVar(value=self._alpaca_base_url())
        self.hint_var = tk.StringVar(value="Choose drivers, start bridge, then connect only the devices you need.")
        self.status_vars = {device_type: tk.StringVar(value="Unknown") for device_type in DEVICE_TYPES}
        self.driver_vars = {device_type: tk.StringVar(value=self._driver_text(device_type)) for device_type in DEVICE_TYPES}
        self.status_labels: dict[str, ctk.CTkLabel] = {}
        self.choose_buttons: dict[str, ctk.CTkButton] = {}
        self.connect_buttons: dict[str, ctk.CTkButton] = {}
        self.pending_devices: set[str] = set()
        self.bridge_button: ctk.CTkButton | None = None

        self._build_ui()
        self._update_bridge_button()
        self._update_device_buttons()
        self._append_log(f"Using {self.config_path}")
        self._append_log("Log messages will appear here.")
        self.after(250, self._drain_logs)
        self.after(1000, self._poll_status)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self, fg_color=COLORS["panel"], border_width=1, border_color=COLORS["line"], corner_radius=8)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="LOCAL ASCOM -> ALPACA HTTP",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(
            row=0, column=0, sticky="ew", padx=10, pady=(8, 0)
        )
        self.bridge_button = ctk.CTkButton(
            header,
            text="Start",
            width=118,
            height=48,
            command=self._bridge_action,
            corner_radius=24,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.bridge_button.grid(row=0, column=1, rowspan=2, sticky="e", padx=10, pady=8)
        ctk.CTkLabel(header, textvariable=self.url_var, anchor="w", text_color=COLORS["muted"]).grid(
            row=1, column=0, sticky="ew", padx=10, pady=(0, 8)
        )

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        controls.grid_columnconfigure(0, weight=1)
        controls.grid_columnconfigure(1, weight=0)
        self._button(controls, "Open Web", self._open_web, 1, width=132, height=44)

        table = ctk.CTkFrame(self, fg_color=COLORS["panel"], border_width=1, border_color=COLORS["line"], corner_radius=8)
        table.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        table.grid_columnconfigure(0, weight=0)
        table.grid_columnconfigure(1, weight=0)
        table.grid_columnconfigure(2, weight=1)
        table.grid_columnconfigure(3, weight=0)
        for row, device_type in enumerate(DEVICE_TYPES):
            self._device_row(table, row, device_type, row % 2 == 0)

        log_frame = ctk.CTkFrame(self, fg_color=COLORS["panel"], border_width=1, border_color=COLORS["line"], corner_radius=8)
        log_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(log_frame, textvariable=self.hint_var, anchor="w", text_color=COLORS["muted"]).grid(
            row=0, column=0, sticky="ew", padx=10, pady=(6, 0)
        )
        self.log_box = ctk.CTkTextbox(
            log_frame,
            height=104,
            fg_color=COLORS["panel_alt"],
            border_width=1,
            border_color=COLORS["line_soft"],
            corner_radius=6,
            text_color=COLORS["text"],
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 10))
        self.log_box.configure(state="disabled")

    def _device_row(self, parent: ctk.CTkFrame, row: int, device_type: str, shaded: bool) -> None:
        row_frame = ctk.CTkFrame(
            parent,
            fg_color=COLORS["row_alt"] if shaded else COLORS["panel"],
            border_width=1,
            border_color=COLORS["line_soft"],
            corner_radius=6,
        )
        row_frame.grid(row=row, column=0, columnspan=4, sticky="ew", padx=6, pady=2)
        row_frame.grid_columnconfigure(0, weight=0)
        row_frame.grid_columnconfigure(1, weight=0)
        row_frame.grid_columnconfigure(2, weight=0)
        row_frame.grid_columnconfigure(3, weight=1)
        row_frame.grid_columnconfigure(4, weight=0)
        ctk.CTkLabel(
            row_frame,
            text=DEVICE_LABELS[device_type],
            anchor="w",
            width=82,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text"],
        ).grid(
            row=0, column=0, sticky="ew", padx=8, pady=5
        )
        button = ctk.CTkButton(
            row_frame,
            text="Choose",
            width=86,
            height=34,
            command=lambda item=device_type: self._choose_device(item),
            fg_color=COLORS["button"],
            hover_color=COLORS["button_hover"],
            border_width=1,
            border_color=COLORS["line"],
            text_color=COLORS["blue"],
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        button.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=5)
        self.choose_buttons[device_type] = button
        status_label = ctk.CTkLabel(
            row_frame,
            textvariable=self.status_vars[device_type],
            anchor="w",
            width=108,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=STATUS_COLORS["Unknown"],
        )
        status_label.grid(
            row=0, column=2, sticky="ew", padx=8, pady=5
        )
        self.status_labels[device_type] = status_label
        ctk.CTkLabel(row_frame, textvariable=self.driver_vars[device_type], anchor="w", text_color=COLORS["muted"]).grid(
            row=0, column=3, sticky="ew", padx=8, pady=5
        )
        connect_button = ctk.CTkButton(
            row_frame,
            text="Connect",
            width=116,
            height=34,
            command=lambda item=device_type: self._device_connection_action(item),
            fg_color=COLORS["blue"],
            hover_color=COLORS["blue_hover"],
            border_width=1,
            border_color=COLORS["blue"],
            text_color=COLORS["white"],
            corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        connect_button.grid(row=0, column=4, sticky="e", padx=(8, 8), pady=5)
        self.connect_buttons[device_type] = connect_button

    def _button(
        self,
        parent: ctk.CTkFrame,
        text: str,
        command: object,
        column: int,
        variant: str = "default",
        width: int | None = None,
        height: int = 30,
    ) -> ctk.CTkButton:
        colors = {
            "default": (COLORS["button"], COLORS["button_hover"], COLORS["line"], COLORS["text"]),
            "primary": (COLORS["blue"], COLORS["blue_hover"], COLORS["blue"], COLORS["white"]),
            "danger": (COLORS["red_soft"], COLORS["red_hover"], COLORS["red_hover"], COLORS["red"]),
        }[variant]
        button = ctk.CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=colors[0],
            hover_color=colors[1],
            border_width=1,
            border_color=colors[2],
            text_color=colors[3],
            corner_radius=6,
            height=height,
            width=width or 0,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        button.grid(row=0, column=column, sticky="ew", padx=4, pady=2)
        return button

    def _set_button_style(self, button: ctk.CTkButton, text: str, variant: str, state: str = "normal") -> None:
        colors = {
            "start": (COLORS["orange"], COLORS["orange_hover"], COLORS["orange"], COLORS["white"]),
            "stop": (COLORS["gray"], COLORS["gray_hover"], COLORS["gray"], COLORS["white"]),
            "external": (COLORS["gray"], COLORS["gray_hover"], COLORS["gray"], COLORS["white"]),
            "connect": (COLORS["blue"], COLORS["blue_hover"], COLORS["blue"], COLORS["white"]),
            "disconnect": (COLORS["red_soft"], COLORS["red_hover"], COLORS["red_hover"], COLORS["red"]),
            "disabled": (COLORS["disabled"], COLORS["disabled"], COLORS["line"], COLORS["muted"]),
        }[variant]
        button.configure(
            text=text,
            fg_color=colors[0],
            hover_color=colors[1],
            border_color=colors[2],
            text_color=colors[3],
            state=state,
        )

    def _bridge_action(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self._stop_bridge()
            return
        if self.bridge_reachable:
            message = "Bridge is running outside this GUI. Stop it from the console/process that started it."
            self._append_log(message)
            messagebox.showinfo(APP_TITLE, message)
            return
        self._start_bridge()

    def _update_bridge_button(self) -> None:
        if self.bridge_button is None:
            return
        process_alive = self.process is not None and self.process.poll() is None
        if process_alive and self.bridge_reachable:
            self._set_button_style(self.bridge_button, "Stop", "stop")
        elif process_alive:
            self._set_button_style(self.bridge_button, "Starting...", "stop")
        elif self.bridge_reachable:
            self._set_button_style(self.bridge_button, "External", "external")
        else:
            self._set_button_style(self.bridge_button, "Start", "start")

    def _update_device_buttons(self) -> None:
        for device_type in DEVICE_TYPES:
            button = self.connect_buttons.get(device_type)
            if button is None:
                continue
            enabled = self.bridge_reachable and self._device_enabled(device_type)
            if device_type in self.pending_devices:
                self._set_button_style(button, "Working...", "disabled", state="disabled")
                continue
            status = self.status_vars[device_type].get()
            if not enabled:
                self._set_button_style(button, "Connect", "disabled", state="disabled")
            elif status == "Connected":
                self._set_button_style(button, "Disconnect", "disconnect")
            elif status == "Busy":
                self._set_button_style(button, "Busy", "disabled", state="disabled")
            else:
                self._set_button_style(button, "Connect", "connect")

    def _device_config(self, device_type: str) -> object:
        return getattr(self.config_data, device_type)

    def _device_enabled(self, device_type: str) -> bool:
        return bool(getattr(self._device_config(device_type), "enabled", True))

    def _driver_text(self, device_type: str) -> str:
        config = self._device_config(device_type)
        suffix = "" if self._device_enabled(device_type) else " (disabled)"
        return f"{config.prog_id}{suffix}"

    def _alpaca_base_url(self) -> str:
        return f"http://127.0.0.1:{self.config_data.server.port}"

    def _device_path(self, device_type: str) -> str:
        config = self._device_config(device_type)
        return f"{self._alpaca_base_url()}/api/v1/{device_type}/{config.device_number}"

    def _refresh_config(self) -> None:
        self.config_data = load_config(self.config_path)
        self.url_var.set(self._alpaca_base_url())
        for device_type in DEVICE_TYPES:
            self.driver_vars[device_type].set(self._driver_text(device_type))

    def _append_log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{timestamp} {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.update_idletasks()

    def _start_bridge(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self._append_log("Bridge is already running.")
            return
        self._refresh_config()
        if self._bridge_available():
            self.bridge_var.set("Bridge: Running (external)")
            self._append_log("Bridge is already reachable on this port. Reusing the existing instance.")
            self.bridge_reachable = True
            self._update_bridge_button()
            self._update_device_buttons()
            return
        command = [sys.executable, "run_bridge.py", "--config", str(self.config_path), "--access-log"]
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
            self.bridge_var.set("Bridge: Error")
            self._update_bridge_button()
            self._update_device_buttons()
            return
        self.bridge_var.set("Bridge: Starting")
        self._update_bridge_button()
        self._append_log("Bridge process started.")
        threading.Thread(target=self._read_process_output, daemon=True).start()

    def _read_process_output(self) -> None:
        if self.process is None or self.process.stdout is None:
            return
        for line in self.process.stdout:
            self.log_queue.put(line.rstrip())

    def _stop_bridge(self) -> None:
        if self.process is None or self.process.poll() is not None:
            if self._bridge_available():
                self.bridge_var.set("Bridge: Running (external)")
                self._append_log("Bridge is running outside this GUI. Stop it from the console/process that started it.")
            else:
                self.bridge_var.set("Bridge: Stopped")
                self._append_log("Bridge is not running.")
            self._update_bridge_button()
            self._update_device_buttons()
            return
        self._append_log("Stopping bridge...")
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._append_log("Force killing bridge.")
            self.process.kill()
        self.bridge_var.set("Bridge: Stopped")
        self.bridge_reachable = False
        self.last_status = None
        if self._bridge_available():
            self.bridge_var.set("Bridge: Running (external)")
            self.bridge_reachable = True
            self._append_log("Bridge port is still reachable; another bridge instance may be running.")
        self._update_choose_state()
        self._update_bridge_button()
        self._update_device_buttons()

    def _open_web(self) -> None:
        webbrowser.open(f"{self._alpaca_base_url()}/")

    def _device_connection_action(self, device_type: str) -> None:
        if device_type in self.pending_devices:
            return
        if not self.bridge_reachable:
            self._append_log("Start the bridge before connecting devices.")
            return
        connected = self._device_connected(device_type)
        self._thread_set_device_connected(device_type, not connected)

    def _thread_set_device_connected(self, device_type: str, connected: bool) -> None:
        self.pending_devices.add(device_type)
        self._update_device_buttons()
        threading.Thread(target=self._set_device_connected_with_log, args=(device_type, connected), daemon=True).start()

    def _set_device_connected_with_log(self, device_type: str, connected: bool) -> None:
        action = "connect" if connected else "disconnect"
        try:
            if not self._bridge_available():
                self.log_queue.put(f"Start the bridge before {action}.")
                return
            if not self._device_enabled(device_type):
                self.log_queue.put(f"{DEVICE_LABELS[device_type]} skipped: disabled.")
                return
            self._set_device_connected(device_type, connected)
        except Exception as exc:
            self.log_queue.put(f"{DEVICE_LABELS[device_type]} {action} failed: {exc}")
        finally:
            self.after(0, lambda item=device_type: self._finish_device_action(item))

    def _finish_device_action(self, device_type: str) -> None:
        self.pending_devices.discard(device_type)
        self._update_device_buttons()

    def _set_device_connected(self, device_type: str, connected: bool) -> None:
        label = "true" if connected else "false"
        payload = {"Connected": label, "ClientTransactionID": str(int(time.time() * 1000) % 1000000)}
        request = Request(
            f"{self._device_path(device_type)}/connected",
            data=urlencode(payload).encode("utf-8"),
            method="PUT",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urlopen(request, timeout=20) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        if response_payload.get("ErrorNumber") != 0:
            raise RuntimeError(response_payload.get("ErrorMessage") or "Alpaca error")
        state = "connected" if connected else "disconnected"
        self.log_queue.put(f"{DEVICE_LABELS[device_type]} {state}.")

    def _bridge_available(self) -> bool:
        if self.process is not None and self.process.poll() is None:
            return True
        try:
            with urlopen(f"{self._alpaca_base_url()}/status", timeout=0.6):
                return True
        except Exception:
            return False

    def _choose_device(self, device_type: str) -> None:
        if not self._choose_allowed():
            message = "Disconnect all devices before choosing drivers."
            self._append_log(message)
            messagebox.showinfo(APP_TITLE, message)
            return
        self._append_log(f"Opening {DEVICE_LABELS[device_type]} chooser...")
        chooser_map = {
            "telescope": choose_telescope,
            "dome": choose_dome,
            "focuser": choose_focuser,
            "camera": choose_camera,
        }
        writer_map = {
            "telescope": write_telescope_prog_id,
            "dome": write_dome_prog_id,
            "focuser": write_focuser_prog_id,
            "camera": write_camera_prog_id,
        }
        try:
            selected = chooser_map[device_type](self._device_config(device_type).prog_id)
        except Exception as exc:
            message = f"{DEVICE_LABELS[device_type]} chooser failed: {exc}"
            self._append_log(message)
            messagebox.showerror(APP_TITLE, message)
            return
        if not selected:
            self._append_log(f"{DEVICE_LABELS[device_type]} chooser cancelled.")
            return
        writer_map[device_type](self.config_path, selected)
        self._refresh_config()
        self._append_log(f"Selected {DEVICE_LABELS[device_type]}: {selected}")
        if self.bridge_reachable:
            self._append_log("Restart bridge to use the new driver selection.")

    def _poll_status(self) -> None:
        if self.process is not None and self.process.poll() is not None:
            self.process = None
            self.bridge_reachable = False
            self.last_status = None
            self.bridge_var.set("Bridge: Stopped")
        try:
            with urlopen(f"{self._alpaca_base_url()}/status", timeout=1.5) as response:
                self.last_status = json.loads(response.read().decode("utf-8"))
            self.status_failures = 0
            self.bridge_reachable = True
            if self.process is not None and self.process.poll() is None:
                self.bridge_var.set("Bridge: Running")
            else:
                self.bridge_var.set("Bridge: Running (external)")
            self._update_device_rows()
        except (OSError, URLError, TimeoutError, json.JSONDecodeError):
            self.status_failures += 1
            if self.bridge_reachable and self.status_failures < 5:
                self.bridge_var.set("Bridge: Busy")
            else:
                if self.process is not None:
                    self.bridge_var.set("Bridge: Starting")
                else:
                    self.bridge_var.set("Bridge: Stopped")
                self.bridge_reachable = False
                self.last_status = None
                self._update_device_rows()
        self._update_choose_state()
        self._update_bridge_button()
        self._update_device_buttons()
        self.after(1000, self._poll_status)

    def _update_device_rows(self) -> None:
        status = self.last_status if isinstance(self.last_status, dict) else {}
        for device_type in DEVICE_TYPES:
            self.driver_vars[device_type].set(self._driver_text(device_type))
            if not self._device_enabled(device_type):
                self.status_vars[device_type].set("Disabled")
                self._set_status_color(device_type, "Disabled")
                continue
            device_status = status.get(device_type)
            if not isinstance(device_status, dict):
                self.status_vars[device_type].set("Unknown")
                self._set_status_color(device_type, "Unknown")
                continue
            error = device_status.get("error")
            connected = device_status.get("connected")
            if device_status.get("busy"):
                self.status_vars[device_type].set("Busy")
                self._set_status_color(device_type, "Busy")
            elif error:
                self.status_vars[device_type].set("Error")
                self._set_status_color(device_type, "Error")
            elif connected is True:
                self.status_vars[device_type].set("Connected")
                self._set_status_color(device_type, "Connected")
            elif connected is False:
                self.status_vars[device_type].set("Disconnected")
                self._set_status_color(device_type, "Disconnected")
            else:
                self.status_vars[device_type].set("Unknown")
                self._set_status_color(device_type, "Unknown")

    def _set_status_color(self, device_type: str, status: str) -> None:
        label = self.status_labels.get(device_type)
        if label is not None:
            label.configure(text_color=STATUS_COLORS.get(status, COLORS["muted"]))

    def _any_connected(self) -> bool:
        status = self.last_status if isinstance(self.last_status, dict) else {}
        for device_type in DEVICE_TYPES:
            device_status = status.get(device_type)
            if isinstance(device_status, dict) and device_status.get("connected") is True:
                return True
        return False

    def _device_connected(self, device_type: str) -> bool:
        status = self.last_status if isinstance(self.last_status, dict) else {}
        device_status = status.get(device_type)
        return isinstance(device_status, dict) and device_status.get("connected") is True

    def _choose_allowed(self) -> bool:
        if not self.bridge_reachable:
            return True
        return not self._any_connected()

    def _update_choose_state(self) -> None:
        allowed = self._choose_allowed()
        state = "normal" if allowed else "disabled"
        for button in self.choose_buttons.values():
            button.configure(state=state)
        if allowed:
            self.hint_var.set("Choose drivers, start bridge, then connect only the devices you need.")
        else:
            self.hint_var.set("Disconnect all devices before choosing drivers.")

    def _drain_logs(self) -> None:
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if line:
                self._append_log(line)
        self.after(250, self._drain_logs)

    def _on_close(self) -> None:
        self._stop_bridge()
        self.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description="ASCOM Alpaca Bridge Simple GUI")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    args = parser.parse_args()
    app = SimpleBridgeGui(args.config)
    app.mainloop()


if __name__ == "__main__":
    main()
