# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Conversão de valores para o SI e de volta, ciente da grandeza.

Regras da seção 6.1 da especificação:

* Temperatura absoluta: °C → K com deslocamento (25 °C = 298,15 K).
* Diferença de temperatura: 1 °C = 1 K, sem deslocamento.
* Nenhuma conta é feita em °C: a conversão para K ocorre na entrada.
* Pressão manométrica só vira absoluta com a pressão atmosférica explícita.
* Porcentagem vira fração.
"""

from __future__ import annotations

from amsior.erros import ErroDeUnidade
from amsior.units.dimensao import dimensao_de_unidade, registro
from amsior.units.glossario import Grandeza

_TROCAS = (
    ("°C", "degC"), ("ºC", "degC"), ("°F", "degF"), ("ºF", "degF"), ("°R", "degR"),
    ("²", "**2"), ("³", "**3"), ("⁴", "**4"), ("·", "*"), ("⋅", "*"), ("µ", "u"),
)
_ESCALAS_COM_ZERO = {"degC": "delta_degC", "degF": "delta_degF"}


def normalizar_unidade(unidade: str) -> str:
    u = unidade.strip()
    for de, para in _TROCAS:
        u = u.replace(de, para)
    return "percent" if u == "%" else u


def _quantidade(valor: float, unidade: str, grandeza: Grandeza) -> object:
    ureg = registro()
    u = normalizar_unidade(unidade)
    if grandeza.temperatura == "diferenca":
        u = _ESCALAS_COM_ZERO.get(u, u)
    elif grandeza.temperatura == "absoluta" and u.startswith("delta_"):
        raise ErroDeUnidade("erro.unidade.diferenca_em_absoluta", unidade=unidade,
                            grandeza=grandeza.nome)
    try:
        dim = dimensao_de_unidade(u)
    except Exception as exc:  # pint levanta vários tipos para unidade desconhecida
        raise ErroDeUnidade("erro.unidade.desconhecida", unidade=unidade) from exc
    if not dim.igual(grandeza.dimensao):
        raise ErroDeUnidade(
            "erro.unidade.incompativel", unidade=unidade, grandeza=grandeza.nome,
            esperada=grandeza.unidade_si,
        )
    return ureg.Quantity(valor, u)


def para_si(valor: float, unidade: str, grandeza: Grandeza) -> float:
    """Valor na unidade SI da grandeza."""
    q = _quantidade(valor, unidade, grandeza)
    alvo = "dimensionless" if grandeza.unidade_si == "1" else grandeza.unidade_si
    return float(q.to(alvo).magnitude)  # type: ignore[attr-defined]


def de_si(valor_si: float, unidade: str, grandeza: Grandeza) -> float:
    """Valor SI convertido para a unidade de exibição."""
    ureg = registro()
    base = "dimensionless" if grandeza.unidade_si == "1" else grandeza.unidade_si
    q = ureg.Quantity(valor_si, base)
    destino = _quantidade(1.0, unidade, grandeza)
    return float(q.to(destino.units).magnitude)  # type: ignore[attr-defined]


def pressao_absoluta(p_manometrica_si: float, p_atmosferica_si: float) -> float:
    """Pressão absoluta a partir da manométrica; a atmosférica é sempre explícita."""
    if p_atmosferica_si <= 0:
        raise ErroDeUnidade("erro.unidade.patm_invalida", valor=p_atmosferica_si)
    return p_manometrica_si + p_atmosferica_si
