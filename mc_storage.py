"""mc_storage.py — armazenamento de imagens com fallback.

Estratégia: se as variáveis de ambiente do Cloudflare R2 estiverem
configuradas, faz upload e guarda a URL pública (leve no Postgres).
Caso contrário, mantém o comportamento atual (base64 embutido no DB).

Ativação (env, configurar no Render — NUNCA commitar):
    R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
    R2_BUCKET, R2_PUBLIC_BASE  (ex.: https://img.mateucoffee.com.br)

Sem essas variáveis, `enabled()` é False e tudo continua em base64 —
zero mudança de comportamento. `img_src()` sabe renderizar os dois formatos,
então fotos antigas (base64) e novas (URL) convivem sem migração.
"""
from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional

import mc_core

_log = mc_core.get_logger()


def _cfg() -> Optional[dict]:
    keys = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
            "R2_BUCKET", "R2_PUBLIC_BASE")
    vals = {k: os.environ.get(k, "") for k in keys}
    if all(vals.values()):
        return vals
    return None


def enabled() -> bool:
    """True se o R2 está configurado por ambiente."""
    return _cfg() is not None


def img_src(ref: Optional[str], mime: str = "image/jpeg") -> str:
    """Converte o valor armazenado em um `src` de <img> utilizável.

    - URL (http...)      → usada direta (foto no R2)
    - data: URI          → usada direta
    - base64 cru         → embrulhada como data URI (fotos legadas no DB)
    - vazio              → string vazia
    """
    if not ref:
        return ""
    r = ref.strip()
    if r.startswith("http://") or r.startswith("https://") or r.startswith("data:"):
        return r
    return f"data:{mime};base64,{r}"


def put_b64(b64: Optional[str], ext: str = "jpg", mime: str = "image/jpeg") -> Optional[str]:
    """Persiste uma imagem (recebida em base64).

    R2 ativo  → faz upload e retorna a URL pública.
    R2 inativo→ retorna o próprio base64 (comportamento atual, sem mudança).
    Falha no upload → degrada para base64 (nunca perde a imagem).
    """
    if not b64:
        return b64
    cfg = _cfg()
    if cfg is None:
        return b64
    try:
        raw = base64.b64decode(b64)
        key = f"img/{hashlib.sha256(raw).hexdigest()[:32]}.{ext}"
        import boto3  # lazy: só quando R2 está ligado
        client = boto3.client(
            "s3",
            endpoint_url=f"https://{cfg['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=cfg["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=cfg["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )
        client.put_object(Bucket=cfg["R2_BUCKET"], Key=key, Body=raw,
                          ContentType=mime, CacheControl="public, max-age=31536000")
        base_url = cfg["R2_PUBLIC_BASE"].rstrip("/")
        return f"{base_url}/{key}"
    except Exception:
        _log.warning("R2: upload falhou — mantendo base64", exc_info=True)
        return b64
