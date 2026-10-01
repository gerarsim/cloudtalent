"""Lance le binaire `alembic` comme le fait le conteneur au démarrage.

Régression : le binaire est exécuté depuis /usr/local/bin, donc `import app`
dans migrations/env.py échouait (ModuleNotFoundError) alors que pytest, qui
ajoute la racine au sys.path, ne voyait rien.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _alembic_cmd() -> list[str]:
    exe = shutil.which("alembic")
    if exe is None:
        pytest.skip("binaire alembic introuvable")
    return [exe]


@pytest.mark.parametrize("cwd_is_root", [True, False], ids=["depuis-backend", "depuis-ailleurs"])
def test_alembic_cli_upgrade_downgrade(tmp_path, cwd_is_root):
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp_path / 'cli.db'}"}
    env.pop("PYTHONPATH", None)  # ne pas masquer le bug par un PYTHONPATH hérité
    cwd = ROOT if cwd_is_root else tmp_path
    for args in (["upgrade", "head"], ["downgrade", "base"], ["upgrade", "head"]):
        r = subprocess.run(
            [*_alembic_cmd(), "-c", str(ROOT / "alembic.ini"), *args],
            cwd=cwd, env=env, capture_output=True, text=True,
        )
        assert r.returncode == 0, f"alembic {' '.join(args)} a échoué :\n{r.stderr}"
