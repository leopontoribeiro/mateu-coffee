"""mc_mail.py — envio de e-mail transacional (Resend).

Fica inerte enquanto RESEND_API_KEY não existir: `enabled()` devolve False e
`send()` não tenta nada. Assim o código do app já pode chamar o envio sem
depender de a conta estar criada — quando a chave entrar no ambiente, o
fluxo passa a funcionar sem alterar mais nada.

Ativação (env no Render — NUNCA commitar):
    RESEND_API_KEY   chave da API
    MAIL_FROM        remetente verificado, ex.: "Mateu Coffee <nao-responda@seu-dominio>"
"""
from __future__ import annotations

import os
from typing import Optional

import requests

import mc_core

_log = mc_core.get_logger()
_API = "https://api.resend.com/emails"


def enabled() -> bool:
    return bool(os.environ.get("RESEND_API_KEY") and os.environ.get("MAIL_FROM"))


def send(para: str, assunto: str, html: str, texto: Optional[str] = None) -> bool:
    """Envia um e-mail. Devolve True só quando o provedor aceitou.

    Nunca levanta: e-mail é acessório em todo fluxo que o chama, e derrubar a
    página do usuário por causa de um provedor fora do ar seria pior.
    """
    if not enabled():
        _log.info("mail: desativado (sem RESEND_API_KEY/MAIL_FROM) — não enviei para %s",
                  para)
        return False
    try:
        payload = {
            "from": os.environ["MAIL_FROM"],
            "to": [para],
            "subject": assunto,
            "html": html,
        }
        if texto:
            payload["text"] = texto
        r = requests.post(
            _API, json=payload, timeout=10,
            headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
                     "Content-Type": "application/json"})
        if r.status_code >= 300:
            _log.warning("mail: provedor recusou (%s): %s", r.status_code, r.text[:200])
            return False
        return True
    except Exception:
        _log.warning("mail: falha no envio", exc_info=True)
        return False


def html_reset_senha(link: str, minutos: int = 30) -> tuple[str, str]:
    """Corpo do e-mail de redefinição — devolve (html, texto)."""
    html = f"""
    <div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;
                max-width:520px;margin:0 auto;color:#2B2724">
      <h2 style="color:#D97732;margin-bottom:4px">Mateu Coffee</h2>
      <p style="font-size:15px;line-height:1.6">
        Recebemos um pedido para redefinir a senha da sua conta.
        O link abaixo vale por <strong>{minutos} minutos</strong> e só pode ser
        usado uma vez.
      </p>
      <p style="margin:28px 0">
        <a href="{link}" style="background:#D97732;color:#fff;text-decoration:none;
           padding:12px 22px;border-radius:8px;font-weight:600;display:inline-block">
          Criar nova senha</a>
      </p>
      <p style="font-size:13px;color:#6B635C;line-height:1.6">
        Se não foi você que pediu, ignore este e-mail — sua senha atual continua
        valendo e nada muda na sua conta.
      </p>
    </div>
    """
    texto = (f"Mateu Coffee — redefinição de senha\n\n"
             f"Use o link abaixo (vale {minutos} minutos, uso único):\n{link}\n\n"
             f"Se não foi você que pediu, ignore este e-mail.")
    return html, texto
