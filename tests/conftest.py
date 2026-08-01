"""Coloca a raiz do projeto no sys.path para os testes importarem os módulos.

Sem isto, `import mc_core` só funciona por acidente — quando outro módulo de
teste que faz o mesmo ajuste roda antes na mesma sessão. Foi assim que a
suíte passou local e quebrou no CI, onde a ordem de coleta era outra.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
