"""Run the SMM Telegram publisher without opening a second HTTP port.

The SMM repository remains independently deployable, but production runs its
publisher inside the existing Render web service so one free instance serves
the dashboard and all Telegram workers.
"""

import asyncio
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
SMM_DIR = ROOT_DIR / "smm-bot-repo"

if not SMM_DIR.is_dir():
    raise RuntimeError(
        "smm-bot-repo is unavailable; initialize the configured git submodule"
    )

sys.path.insert(0, str(SMM_DIR))

from smm_reklam import run_publisher  # noqa: E402


if __name__ == "__main__":
    asyncio.run(run_publisher())
