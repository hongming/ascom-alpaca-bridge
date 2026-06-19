from __future__ import annotations

import argparse
import json
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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


class BridgeGui(ctk.CTk):
    def __init__(self, config_path: str | Path = "config.yaml") -> None:
        super().__init__()
        self.config_path = Path(config_path)
        self.title(APP_TITLE)
        self.geometry("1120x820")
        self.minsize(980, 720)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.process: subprocess.Popen[str] | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.config_data = load_config(self.config_path)

        self.status_var = tk.StringVar(value="Stopped")
        self.url_var = tk.StringVar(value=self._alpaca_base_url())
        self.telescope_status_var = tk.StringVar(value="--")
        self.dome_status_var = tk.StringVar(value="--")
        self.focuser_status_var = tk.StringVar(value="--")
        self.camera_status_var = tk.StringVar(value="--")

        self.telescope_prog_var = tk.StringVar(value=self.config_data.telescope.prog_id)
        self.dome_prog_var = tk.StringVar(value=self._enabled_prog("dome"))
        self.focuser_prog_var = tk.StringVar(value=self._enabled_prog("focuser"))
        self.camera_prog_var = tk.StringVar(value=self._enabled_prog("camera"))

        self.telescope_ra_var = tk.StringVar(value="")
        self.telescope_dec_var = tk.StringVar(value="")
        self.dome_az_var = tk.StringVar(value="180")
        self.focuser_position_var = tk.StringVar(value="12000")
        self.camera_duration_var = tk.StringVar(value="1")
        self.camera_temp_var = tk.StringVar(value="-10")

        self._build_ui()
        self._append_log(f"Using config: {self.config_path}")
        self.after(250, self._drain_logs)
        self.after(1000, self._poll_status)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 12))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text=APP_TITLE, font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 2)
        )
        ctk.CTkLabel(header, textvariable=self.url_var, anchor="w").grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10)
        )
        ctk.CTkLabel(header, textvariable=self.status_var, anchor="e").grid(
            row=0, column=1, sticky="e", padx=12, pady=(10, 2)
        )

        top_buttons = ctk.CTkFrame(self, fg_color="transparent")
        top_buttons.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        for column in range(5):
            top_buttons.grid_columnconfigure(column, weight=1)
        self._button(top_buttons, "Start Bridge", self._start_bridge, 0, 0)
        self._button(top_buttons, "Stop Bridge", self._stop_bridge, 0, 1)
        self._button(top_buttons, "Open Web", self._open_web, 0, 2)
        self._button(top_buttons, "Open Status", self._open_status, 0, 3)
        self._button(top_buttons, "Copy URL", self._copy_url, 0, 4)

        devices = ctk.CTkFrame(self)
        devices.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        for column in range(2):
            devices.grid_columnconfigure(column, weight=1)
        self._build_telescope_panel(devices).grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        self._build_dome_panel(devices).grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))
        self._build_focuser_panel(devices).grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(8, 0))
        self._build_camera_panel(devices).grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(8, 0))

        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=3, column=0, sticky="nsew", padx=18, pady=(0, 18))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(log_frame, text="Log", anchor="w", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="ew", padx=12, pady=(10, 4)
        )
        self.log_box = ctk.CTkTextbox(log_frame, height=160)
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.log_box.configure(state="disabled")

    def _build_telescope_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        frame = self._device_panel(parent, "Telescope", self.telescope_status_var, self.telescope_prog_var)
        controls = self._panel_controls(frame, 3)
        self._button(controls, "Choose", lambda: self._choose_device("telescope"), 0, 0)
        self._button(controls, "Connect", lambda: self._thread_put("telescope", "connected", {"Connected": "true"}), 0, 1)
        self._button(controls, "Disconnect", lambda: self._thread_put("telescope", "connected", {"Connected": "false"}), 0, 2)
        self._button(controls, "Tracking On", lambda: self._thread_put("telescope", "tracking", {"Tracking": "true"}), 1, 0)
        self._button(controls, "Tracking Off", lambda: self._thread_put("telescope", "tracking", {"Tracking": "false"}), 1, 1)
        self._button(controls, "Abort Slew", lambda: self._thread_put("telescope", "abortslew"), 1, 2)

        slew = self._field_row(frame, 4)
        self._entry(slew, "RA h", self.telescope_ra_var, 0)
        self._entry(slew, "DEC deg", self.telescope_dec_var, 1)
        self._button(
            slew,
            "Slew",
            lambda: self._thread_put(
                "telescope",
                "slewtocoordinatesasync",
                {"RightAscension": self.telescope_ra_var.get(), "Declination": self.telescope_dec_var.get()},
            ),
            0,
            4,
        )

        park = self._panel_controls(frame, 5)
        self._button(park, "Park", lambda: self._thread_put("telescope", "park"), 0, 0)
        self._button(park, "Unpark", lambda: self._thread_put("telescope", "unpark"), 0, 1)
        self._button(park, "Find Home", lambda: self._thread_put("telescope", "findhome"), 0, 2)
        return frame

    def _build_dome_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        frame = self._device_panel(parent, "Dome", self.dome_status_var, self.dome_prog_var)
        controls = self._panel_controls(frame, 3)
        self._button(controls, "Choose", lambda: self._choose_device("dome"), 0, 0)
        self._button(controls, "Connect", lambda: self._thread_put("dome", "connected", {"Connected": "true"}), 0, 1)
        self._button(controls, "Disconnect", lambda: self._thread_put("dome", "connected", {"Connected": "false"}), 0, 2)
        self._button(controls, "Open Shutter", lambda: self._thread_put("dome", "openshutter"), 1, 0)
        self._button(controls, "Close Shutter", lambda: self._thread_put("dome", "closeshutter"), 1, 1)
        self._button(controls, "Abort Slew", lambda: self._thread_put("dome", "abortslew"), 1, 2)

        slew = self._field_row(frame, 4)
        self._entry(slew, "Az deg", self.dome_az_var, 0)
        self._button(slew, "Slew Az", lambda: self._thread_put("dome", "slewtoazimuth", {"Azimuth": self.dome_az_var.get()}), 0, 2)
        self._button(slew, "Sync Az", lambda: self._thread_put("dome", "synctoazimuth", {"Azimuth": self.dome_az_var.get()}), 0, 3)

        extra = self._panel_controls(frame, 5)
        self._button(extra, "Slave On", lambda: self._thread_put("dome", "slaved", {"Slaved": "true"}), 0, 0)
        self._button(extra, "Slave Off", lambda: self._thread_put("dome", "slaved", {"Slaved": "false"}), 0, 1)
        self._button(extra, "Park", lambda: self._thread_put("dome", "park"), 0, 2)
        return frame

    def _build_focuser_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        frame = self._device_panel(parent, "Focuser", self.focuser_status_var, self.focuser_prog_var)
        controls = self._panel_controls(frame, 3)
        self._button(controls, "Choose", lambda: self._choose_device("focuser"), 0, 0)
        self._button(controls, "Connect", lambda: self._thread_put("focuser", "connected", {"Connected": "true"}), 0, 1)
        self._button(controls, "Disconnect", lambda: self._thread_put("focuser", "connected", {"Connected": "false"}), 0, 2)

        move = self._field_row(frame, 4)
        self._entry(move, "Position", self.focuser_position_var, 0)
        self._button(move, "Move", lambda: self._thread_put("focuser", "move", {"Position": self.focuser_position_var.get()}), 0, 2)
        self._button(move, "Halt", lambda: self._thread_put("focuser", "halt"), 0, 3)

        tempcomp = self._panel_controls(frame, 5)
        self._button(tempcomp, "TempComp On", lambda: self._thread_put("focuser", "tempcomp", {"TempComp": "true"}), 0, 0)
        self._button(tempcomp, "TempComp Off", lambda: self._thread_put("focuser", "tempcomp", {"TempComp": "false"}), 0, 1)
        return frame

    def _build_camera_panel(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        frame = self._device_panel(parent, "Camera", self.camera_status_var, self.camera_prog_var)
        controls = self._panel_controls(frame, 3)
        self._button(controls, "Choose", lambda: self._choose_device("camera"), 0, 0)
        self._button(controls, "Connect", lambda: self._thread_put("camera", "connected", {"Connected": "true"}), 0, 1)
        self._button(controls, "Disconnect", lambda: self._thread_put("camera", "connected", {"Connected": "false"}), 0, 2)

        exposure = self._field_row(frame, 4)
        self._entry(exposure, "Duration s", self.camera_duration_var, 0)
        self._button(
            exposure,
            "Expose Light",
            lambda: self._thread_put("camera", "startexposure", {"Duration": self.camera_duration_var.get(), "Light": "true"}),
            0,
            2,
        )
        self._button(
            exposure,
            "Expose Dark",
            lambda: self._thread_put("camera", "startexposure", {"Duration": self.camera_duration_var.get(), "Light": "false"}),
            0,
            3,
        )

        actions = self._panel_controls(frame, 5)
        self._button(actions, "Stop Exposure", lambda: self._thread_put("camera", "stopexposure"), 0, 0)
        self._button(actions, "Abort Exposure", lambda: self._thread_put("camera", "abortexposure"), 0, 1)
        self._button(actions, "Cooler On", lambda: self._thread_put("camera", "cooleron", {"CoolerOn": "true"}), 0, 2)
        self._button(actions, "Cooler Off", lambda: self._thread_put("camera", "cooleron", {"CoolerOn": "false"}), 0, 3)

        temp = self._field_row(frame, 6)
        self._entry(temp, "Temp C", self.camera_temp_var, 0)
        self._button(
            temp,
            "Set Temp",
            lambda: self._thread_put("camera", "setccdtemperature", {"SetCCDTemperature": self.camera_temp_var.get()}),
            0,
            2,
        )
        self._button(temp, "Open Camera Web", self._open_web, 0, 3)
        return frame

    def _device_panel(
        self,
        parent: ctk.CTkFrame,
        title: str,
        status_var: tk.StringVar,
        prog_var: tk.StringVar,
    ) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=title, anchor="w", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="ew", padx=12, pady=(10, 2)
        )
        ctk.CTkLabel(frame, textvariable=status_var, anchor="w").grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 2))
        ctk.CTkLabel(frame, textvariable=prog_var, anchor="w", text_color="gray").grid(
            row=2, column=0, sticky="ew", padx=12, pady=(0, 8)
        )
        return frame

    def _panel_controls(self, parent: ctk.CTkFrame, row: int) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=12, pady=(0, 8))
        for column in range(4):
            frame.grid_columnconfigure(column, weight=1)
        return frame

    def _field_row(self, parent: ctk.CTkFrame, row: int) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=12, pady=(0, 8))
        for column in range(5):
            frame.grid_columnconfigure(column, weight=1)
        return frame

    def _button(self, parent: ctk.CTkBaseClass, text: str, command: object, row: int, column: int) -> ctk.CTkButton:
        button = ctk.CTkButton(parent, text=text, command=command)
        button.grid(row=row, column=column, sticky="ew", padx=4, pady=4)
        return button

    def _entry(self, parent: ctk.CTkFrame, label: str, variable: tk.StringVar, column: int) -> None:
        ctk.CTkLabel(parent, text=label, anchor="w").grid(row=0, column=column, sticky="ew", padx=4, pady=4)
        entry = ctk.CTkEntry(parent, textvariable=variable)
        entry.grid(row=0, column=column + 1, sticky="ew", padx=4, pady=4)

    def _enabled_prog(self, device_type: str) -> str:
        config = getattr(self.config_data, device_type)
        if not getattr(config, "enabled", True):
            return f"{config.prog_id} (disabled)"
        return config.prog_id

    def _alpaca_base_url(self) -> str:
        return f"http://127.0.0.1:{self.config_data.server.port}"

    def _device_number(self, device_type: str) -> int:
        return int(getattr(self.config_data, device_type).device_number)

    def _device_path(self, device_type: str) -> str:
        return f"{self._alpaca_base_url()}/api/v1/{device_type}/{self._device_number(device_type)}"

    def _refresh_config(self) -> None:
        self.config_data = load_config(self.config_path)
        self.url_var.set(self._alpaca_base_url())
        self.telescope_prog_var.set(self.config_data.telescope.prog_id)
        self.dome_prog_var.set(self._enabled_prog("dome"))
        self.focuser_prog_var.set(self._enabled_prog("focuser"))
        self.camera_prog_var.set(self._enabled_prog("camera"))

    def _append_log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{timestamp} {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.update_idletasks()

    def _choose_device(self, device_type: str) -> None:
        if self.process is not None and self.process.poll() is None:
            message = "Stop the bridge before choosing a new driver."
            self._append_log(message)
            messagebox.showinfo(APP_TITLE, message)
            return
        self._append_log(f"Opening {device_type.title()} chooser...")
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
        current = getattr(self.config_data, device_type).prog_id
        try:
            selected = chooser_map[device_type](current)
        except Exception as exc:
            message = f"{device_type.title()} chooser failed: {exc}"
            self._append_log(message)
            messagebox.showerror(APP_TITLE, message)
            return
        if not selected:
            self._append_log(f"{device_type.title()} chooser cancelled.")
            return
        writer_map[device_type](self.config_path, selected)
        self._refresh_config()
        self._append_log(f"Selected {device_type}: {selected}")

    def _start_bridge(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self._append_log("Bridge is already running.")
            return
        self._refresh_config()
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
        self.clipboard_append(self._alpaca_base_url())
        self._append_log("Base URL copied.")

    def _open_web(self) -> None:
        webbrowser.open(f"{self._alpaca_base_url()}/")

    def _open_status(self) -> None:
        webbrowser.open(f"{self._alpaca_base_url()}/status")

    def _thread_put(self, device_type: str, member: str, data: dict[str, str] | None = None) -> None:
        threading.Thread(target=self._put_member, args=(device_type, member, data or {}), daemon=True).start()

    def _put_member(self, device_type: str, member: str, data: dict[str, str]) -> None:
        if self.process is None or self.process.poll() is not None:
            self.log_queue.put("Start the bridge before sending device commands.")
            return
        payload = {"ClientTransactionID": str(int(time.time() * 1000) % 1000000), **data}
        request = Request(
            f"{self._device_path(device_type)}/{member}",
            data=urlencode(payload).encode("utf-8"),
            method="PUT",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urlopen(request, timeout=20) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            self.log_queue.put(f"{device_type.title()} {member} failed: {exc}")
            return
        if response_payload.get("ErrorNumber") == 0:
            self.log_queue.put(f"{device_type.title()} {member} OK.")
        else:
            self.log_queue.put(f"{device_type.title()} {member} error: {response_payload.get('ErrorMessage')}")

    def _read_value(self, device_type: str, member: str, timeout: float = 0.5) -> object | None:
        try:
            with urlopen(f"{self._device_path(device_type)}/{member}", timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None
        if payload.get("ErrorNumber") != 0:
            return None
        return payload.get("Value")

    def _format_bool(self, value: object) -> str:
        if value is True:
            return "Connected"
        if value is False:
            return "Disconnected"
        return "--"

    def _poll_status(self) -> None:
        if self.process is not None and self.process.poll() is not None:
            self.status_var.set("Stopped")
        elif self.process is not None:
            try:
                with urlopen(f"{self._alpaca_base_url()}/status", timeout=0.5) as response:
                    data = json.loads(response.read().decode("utf-8"))
                self.status_var.set("Running")
                self._update_device_statuses(data)
            except (OSError, URLError, TimeoutError, json.JSONDecodeError):
                self.status_var.set("Starting")
        self.after(1000, self._poll_status)

    def _update_device_statuses(self, status: dict[str, object]) -> None:
        for device_type, variable in (
            ("telescope", self.telescope_status_var),
            ("dome", self.dome_status_var),
            ("focuser", self.focuser_status_var),
            ("camera", self.camera_status_var),
        ):
            device = status.get(device_type)
            if not isinstance(device, dict):
                variable.set("--")
                continue
            connected = device.get("connected")
            text = self._format_bool(connected)
            error = device.get("error")
            if error:
                text = f"{text} / {error}"
            variable.set(text)

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
    parser = argparse.ArgumentParser(description="ASCOM Alpaca Bridge GUI")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    args = parser.parse_args()
    app = BridgeGui(args.config)
    app.mainloop()


if __name__ == "__main__":
    main()
