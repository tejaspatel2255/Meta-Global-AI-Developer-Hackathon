"""Start API (:8000) and Vite (:5173) together."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend") + os.pathsep + env.get("PYTHONPATH", "")
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "benchguard.api.app:app",
            "--reload",
            "--app-dir",
            str(ROOT / "backend"),
            "--port",
            "8000",
        ],
        cwd=ROOT,
        env=env,
    )
    ui = subprocess.Popen(["npm", "run", "dev"], cwd=ROOT / "frontend", shell=os.name == "nt")
    try:
        api.wait()
        ui.wait()
    except KeyboardInterrupt:
        api.terminate()
        ui.terminate()


if __name__ == "__main__":
    main()
