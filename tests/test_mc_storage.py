"""Testes do mc_storage — garante que SEM R2 o comportamento é base64 puro
(idêntico ao legado) e que img_src rende os dois formatos.
Rodar: pytest -q
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import mc_storage


def test_desativado_sem_env(monkeypatch):
    for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
              "R2_BUCKET", "R2_PUBLIC_BASE"):
        monkeypatch.delenv(k, raising=False)
    assert mc_storage.enabled() is False
    # sem R2 → devolve o próprio base64, sem tocar em rede
    assert mc_storage.put_b64("QUJD") == "QUJD"
    assert mc_storage.put_b64(None) is None
    assert mc_storage.put_b64("") == ""


def test_img_src_formatos():
    assert mc_storage.img_src("QUJD") == "data:image/jpeg;base64,QUJD"
    assert mc_storage.img_src("https://x/y.jpg") == "https://x/y.jpg"
    assert mc_storage.img_src("http://x/y.jpg") == "http://x/y.jpg"
    assert mc_storage.img_src("data:image/png;base64,ZZ") == "data:image/png;base64,ZZ"
    assert mc_storage.img_src("") == ""
    assert mc_storage.img_src(None) == ""


def test_enabled_com_env_completo(monkeypatch):
    for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
              "R2_BUCKET", "R2_PUBLIC_BASE"):
        monkeypatch.setenv(k, "x")
    assert mc_storage.enabled() is True
