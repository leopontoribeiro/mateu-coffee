"""
Entry point do Render/Streamlit Cloud.
Delega para streamlit_app_final.py (app completo).
"""
import os

_here = os.path.dirname(os.path.abspath(__file__))
_main = os.path.join(_here, "streamlit_app_final.py")

with open(_main, encoding="utf-8") as _f:
    exec(compile(_f.read(), _main, "exec"), globals())  # noqa: S102
