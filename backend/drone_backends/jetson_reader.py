"""
NVIDIA Jetson hardware reader via SSH.

Connects to a Jetson board (Orin Nano / NX / AGX) over the network and reads:
  - Board model and serial number
  - CPU/GPU utilization and temperature
  - RAM and disk capacity
  - CUDA and TensorRT versions
  - Connected cameras (V4L2 devices)
  - ROS 2 installation status
"""

from __future__ import annotations

import re
from typing import Any

# Jetson model → hardware specs (GPU SM count, max TDP, default RAM GB)
_JETSON_SPECS: dict[str, dict] = {
    "orin nano":  {"gpu_sms": 512,  "max_tdp_w": 15,  "ram_gb": 8,  "nvdla": 1},
    "orin nx 8":  {"gpu_sms": 1024, "max_tdp_w": 20,  "ram_gb": 8,  "nvdla": 2},
    "orin nx 16": {"gpu_sms": 1024, "max_tdp_w": 25,  "ram_gb": 16, "nvdla": 2},
    "agx orin":   {"gpu_sms": 2048, "max_tdp_w": 60,  "ram_gb": 32, "nvdla": 2},
}


class JetsonReader:
    """Synchronous Jetson SSH reader — run in a thread pool from async code."""

    def __init__(self):
        self._client = None
        self._host: str = ""

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self, host: str, username: str = "jetson",
                password: str | None = None, key_path: str | None = None,
                port: int = 22, timeout: float = 10.0) -> dict[str, Any]:
        try:
            import paramiko
        except ImportError:
            return {"ok": False, "error": "paramiko not installed — run: pip install paramiko"}

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            kwargs: dict = {
                "hostname": host,
                "port":     port,
                "username": username,
                "timeout":  timeout,
            }
            if key_path:
                kwargs["key_filename"] = key_path
            elif password:
                kwargs["password"] = password
            else:
                kwargs["look_for_keys"] = True

            client.connect(**kwargs)
            self._client = client
            self._host   = host
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
        self._client = None

    @property
    def connected(self) -> bool:
        transport = self._client.get_transport() if self._client else None
        return transport is not None and transport.is_active()

    # ── Read ──────────────────────────────────────────────────────────────────

    def read_parameters(self) -> dict[str, Any]:
        if not self.connected:
            return {"ok": False, "error": "Not connected"}
        try:
            model    = self._run("cat /proc/device-tree/model 2>/dev/null | tr -d '\\0'")
            ram_gb   = self._parse_ram()
            disk_gb  = self._parse_disk()
            cpu_cores = self._parse_int("nproc", 8)
            cuda_ver = self._parse_cuda()
            trt_ver  = self._parse_trt()
            cameras  = self._parse_cameras()
            ros2     = self._parse_ros2()
            temps    = self._parse_temps()

            # Match model to known specs
            specs: dict = {}
            for key, val in _JETSON_SPECS.items():
                if key in model.lower():
                    specs = val
                    break

            profile = {
                "board_type": "jetson",
                "firmware": {
                    "model":      model.strip(),
                    "cuda":       cuda_ver,
                    "tensorrt":   trt_ver,
                    "ros2":       ros2,
                },
                "compute": {
                    "cpu_cores":  cpu_cores,
                    "ram_gb":     ram_gb,
                    "disk_free_gb": disk_gb,
                    "gpu_sms":    specs.get("gpu_sms", "unknown"),
                    "nvdla":      specs.get("nvdla", 0),
                    "max_tdp_w":  specs.get("max_tdp_w", "unknown"),
                    "temperatures": temps,
                },
                "cameras": cameras,
                "imu": {
                    "sensor":            "EXTERNAL",
                    "acc_noise_density": 1.4e-3,
                    "gyro_noise_density": 8.7e-5,
                    "acc_random_walk":   1.0e-4,
                    "gyro_random_walk":  2.2e-6,
                    "rate_hz":           200,
                    "note": "Set IMU params from the flight controller profile",
                },
                "vehicle": {
                    "frame_type":  "QUAD_X",
                    "motor_count": 4,
                },
                "battery": {
                    "cells": 4,
                },
            }
            return {"ok": True, "profile": profile}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── SSH helpers ───────────────────────────────────────────────────────────

    def _run(self, cmd: str) -> str:
        _, stdout, _ = self._client.exec_command(cmd, timeout=5)
        return stdout.read().decode("utf-8", errors="replace").strip()

    def _parse_int(self, cmd: str, default: int) -> int:
        try:
            return int(self._run(cmd))
        except (ValueError, TypeError):
            return default

    def _parse_ram(self) -> float:
        out = self._run("free -m | awk '/^Mem:/{print $2}'")
        try:
            return round(int(out) / 1024, 1)
        except (ValueError, TypeError):
            return 0.0

    def _parse_disk(self) -> float:
        out = self._run("df -BG / | awk 'NR==2{print $4}' | tr -d 'G'")
        try:
            return float(out)
        except (ValueError, TypeError):
            return 0.0

    def _parse_cuda(self) -> str:
        out = self._run("nvcc --version 2>/dev/null | grep -o 'release [0-9.]*' | head -1")
        if out:
            return out.replace("release ", "")
        out = self._run("cat /usr/local/cuda/version.txt 2>/dev/null | head -1")
        m = re.search(r"[0-9]+\.[0-9]+", out)
        return m.group(0) if m else "not found"

    def _parse_trt(self) -> str:
        out = self._run(
            "python3 -c \"import tensorrt; print(tensorrt.__version__)\" 2>/dev/null")
        return out.strip() if out else "not found"

    def _parse_cameras(self) -> list[dict]:
        out = self._run("ls /dev/video* 2>/dev/null")
        devices = [d.strip() for d in out.splitlines() if d.strip()]
        cameras = []
        for dev in devices:
            name = self._run(
                f"v4l2-ctl --device={dev} --info 2>/dev/null | "
                "grep 'Card type' | cut -d: -f2 | xargs")
            cameras.append({"device": dev, "name": name or "unknown"})
        return cameras

    def _parse_ros2(self) -> str:
        out = self._run(
            "source /opt/ros/humble/setup.bash 2>/dev/null && ros2 --version 2>/dev/null"
            " || echo 'not found'")
        return out.strip()

    def _parse_temps(self) -> dict[str, float]:
        out = self._run(
            "cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -8")
        temps: dict[str, float] = {}
        names = self._run(
            "cat /sys/class/thermal/thermal_zone*/type 2>/dev/null | head -8")
        for i, (t_str, n_str) in enumerate(
                zip(out.splitlines(), names.splitlines())):
            try:
                temps[n_str.strip()] = round(int(t_str.strip()) / 1000.0, 1)
            except (ValueError, TypeError):
                pass
        return temps
