from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_dir = Path(__file__).resolve().parents[1]
    log_dir = project_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "windows_server.log"

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    command = [sys.executable, "-m", "app"]

    with log_path.open("w", encoding="utf-8", errors="replace") as log_file:
        log_file.write("Jump Caption Windows server log\n")
        log_file.write(f"python: {sys.executable}\n")
        log_file.write(f"command: {' '.join(command)}\n\n")
        log_file.flush()

        process = subprocess.Popen(
            command,
            cwd=project_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            log_file.write(line)
            log_file.flush()

        return_code = process.wait()
        message = f"\nJump Caption server exited with code {return_code}\n"
        print(message, end="")
        log_file.write(message)
        return return_code


if __name__ == "__main__":
    raise SystemExit(main())
