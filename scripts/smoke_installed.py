"""Exercise an installed wheel from outside the source tree; no API credentials."""
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile

import openactionproof


def main():
    version = importlib.metadata.version("open-action-proof")
    assert version == openactionproof.__version__, (version, openactionproof.__version__)
    root = Path(__file__).resolve().parents[1]
    assert not Path(openactionproof.__file__).resolve().is_relative_to(root / "src")
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory() as temp:
        cwd = Path(temp)
        def run(*args):
            return subprocess.run(args, cwd=cwd, env=env, check=True, capture_output=True, text=True, timeout=60).stdout
        cli = shutil.which("oap", path=sysconfig.get_path("scripts"))
        assert cli, "installed console entry point missing"
        verdicts = json.loads(run(cli, "demo", "--output", "receipts"))
        assert verdicts == {"A_confirmed":"CONFIRMED", "B_false_success":"FALSE_SUCCESS", "C_partial_timeout":"INDETERMINATE"}
        assert run(cli, "verify-receipt", "receipts/A_confirmed.json").strip() == "CHECKSUM_VALID"
        http = json.loads(run(sys.executable, "-m", "openactionproof.http_lab"))
        assert http["exact_verdict_matches"] == http["fixture_count"] == 14
        observation = json.loads(run(sys.executable, "-m", "openactionproof.observation_benchmark"))
        assert observation["exact_matches"] == observation["cases"] == 16
    print(json.dumps({"version":version,"installed_from":str(Path(openactionproof.__file__).resolve()),"file_cases":3,"http_cases":14,"observation_cases":16,"status":"passed"}, sort_keys=True))


if __name__ == "__main__":
    main()
