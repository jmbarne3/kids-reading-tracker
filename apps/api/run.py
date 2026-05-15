import subprocess
import sys

if __name__ == "__main__":
    subprocess.run(
        [sys.executable, "manage.py", "runserver", "0.0.0.0:8000"],
        check=True,
    )
