import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skill"))


import urllib.error  # noqa: E402
import urllib.request  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _sin_red(monkeypatch):
    """Los tests no salen a internet ni usan la API de DataFondos que esté
    configurada en la máquina: los que las necesitan las simulan."""
    for variable in ("DATAFONDOS_API_URL", "DATAFONDOS_API_KEY", "DATAFONDOS_TIMEOUT"):
        monkeypatch.delenv(variable, raising=False)

    def sin_red(*args, **kwargs):
        raise urllib.error.URLError("los tests no salen a internet")

    monkeypatch.setattr(urllib.request, "urlopen", sin_red)
