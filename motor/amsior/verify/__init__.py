# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Verificação: certificados por passo (V1, V5) e de solução (V2)."""

from amsior.verify.certificador import Verificador, certificar, provavel
from amsior.verify.identidade import ResultadoIdentidade, identicas
from amsior.verify.modelo import (
    Certificado, Condicao, Motivo, Operacao, Passo, Relacao, TipoPasso,
)
from amsior.verify.operacoes import OPERACOES

__all__ = [
    "OPERACOES", "Certificado", "Condicao", "Motivo", "Operacao", "Passo", "Relacao",
    "ResultadoIdentidade", "TipoPasso", "Verificador", "certificar", "identicas", "provavel",
]
