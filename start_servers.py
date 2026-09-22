import subprocess
import sys
import time
import os
import signal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def run_services():
    print("=" * 70)
    print("   LEGAL METROLOGY (PACKAGED COMMODITIES) COMPLIANCE SYSTEM")
    print("   Smart India Hackathon Problem Statement SIH26034")
    print("=" * 70)
    print(" Starting Backend & Frontend servers on distinct localhost ports:")
    print("   * Backend API:       http://localhost:8088")
    print("   * Interactive UI:    http://localhost:5188")
    print("   * API Documentation: http://localhost:8088/docs")
    print("=" * 70)
    print(" Press Ctrl+C to safely terminate both servers.\n")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE_DIR / "backend")

    backend_proc = subprocess.Popen(
        [sys.executable, str(BASE_DIR / "backend" / "run_backend.py")],
        cwd=str(BASE_DIR / "backend"),
        env=env
    )

    time.sleep(1)

    frontend_proc = subprocess.Popen(
        [sys.executable, str(BASE_DIR / "frontend" / "serve_frontend.py")],
        cwd=str(BASE_DIR / "frontend")
    )

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("Backend terminated unexpectedly.")
                break
            if frontend_proc.poll() is not None:
                print("Frontend terminated unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\nStopping all services...")
    finally:
        try:
            backend_proc.terminate()
            frontend_proc.terminate()
        except Exception:
            pass
        print("All servers stopped.")

if __name__ == "__main__":
    run_services()
