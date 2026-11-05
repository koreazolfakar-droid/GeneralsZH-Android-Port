#!/usr/bin/env python3
"""Run the bounded catch-up budget and implementation wiring checks."""
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[2]
subprocess.run(['bash', str(ROOT/'scripts/qa/test-engine-budget-v2.sh')], cwd=ROOT, check=True)
