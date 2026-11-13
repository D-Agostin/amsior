# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Registro de passo, condições, operação declarada e certificado (seção 3.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from amsior.expr.json_io import de_json, para_json
from amsior.expr.nos import Expr, Sym

TipoPasso = Literal["algebra", "calculo", "substituicao", "principio", "aproximacao", "numerico"]
Relacao = Literal["equivalente", "implica", "restringe"]
OrigemCondicao = Literal["suposicao", "hipotese"]
Lado = Literal["esquerdo", "direito", "ambos"]
MetodoCert = Literal["simbolico", "numerico", "revisao_humana"]
EstadoCert = Literal["aprovado", "reprovado", "pendente"]

RELACOES: tuple[Relacao, ...] = ("equivalente", "restringe", "implica")


@dataclass(frozen=True)
class Condicao:
    """Condição como relação (``Ne``, ``Gt``, ``Ge``, ``Lt``, ``Le``)."""

    expr: Expr
    origem: OrigemCondicao = "hipotese"
    satisfeita: bool | None = None

    def para_json(self) -> dict[str, Any]:
        return {"expr": para_json(self.expr), "origem": self.origem,
                "satisfeita": self.satisfeita}

    @staticmethod
    def de_json(d: dict[str, Any]) -> Condicao:
        return Condicao(de_json(d["expr"]), d.get("origem", "hipotese"), d.get("satisfeita"))


@dataclass(frozen=True)
class Operacao:
    """Operação declarada, em forma que o verificador refaz sozinho.

    ``nome`` é uma das operações da tabela do verificador
    (``amsior.verify.operacoes.OPERACOES``).
    """

    nome: str
    argumento: Expr | None = None
    lado: Lado | None = None
    simbolo: Sym | None = None
    origem: Literal["definicao", "hipotese"] | None = None

    def para_json(self) -> dict[str, Any]:
        return {
            "nome": self.nome,
            "argumento": None if self.argumento is None else para_json(self.argumento),
            "lado": self.lado,
            "simbolo": None if self.simbolo is None else para_json(self.simbolo),
            "origem": self.origem,
        }

    @staticmethod
    def de_json(d: dict[str, Any]) -> Operacao:
        simb = None if d.get("simbolo") is None else de_json(d["simbolo"])
        assert simb is None or isinstance(simb, Sym)
        return Operacao(
            d["nome"],
            None if d.get("argumento") is None else de_json(d["argumento"]),
            d.get("lado"), simb, d.get("origem"),
        )


@dataclass(frozen=True)
class Motivo:
    """Motivo de aprovação ou reprovação. Argumentos que são chaves do catálogo
    (``predicado.*``, ``verif.identidade.*``) são traduzidos na exibição."""

    chave: str
    args: dict[str, str] = field(default_factory=dict)

    def texto(self, idioma: str = "pt-BR") -> str:
        from amsior.i18n import catalogo, t

        cat = catalogo("pt-BR")
        args = {k: (t(v, idioma) if v in cat else v) for k, v in self.args.items()}
        return t(self.chave, idioma, **args)


@dataclass
class Certificado:
    metodo: MetodoCert
    estado: EstadoCert
    motivos: list[Motivo] = field(default_factory=list)
    v1: str = "pendente"
    v5: str = "pendente"
    relacoes_permitidas: tuple[Relacao, ...] = ()

    def para_json(self) -> dict[str, Any]:
        return {
            "metodo": self.metodo, "estado": self.estado,
            "motivos": [{"chave": m.chave, "args": m.args} for m in self.motivos],
            "v1": self.v1, "v5": self.v5,
            "relacoes_permitidas": list(self.relacoes_permitidas),
        }


@dataclass
class Passo:
    antes: Expr
    depois: Expr
    operacao: Operacao
    relacao: Relacao = "equivalente"
    tipo: TipoPasso = "algebra"
    indice: int = 0
    regra: str = ""
    condicoes: tuple[Condicao, ...] = ()
    justificativa: dict[str, Any] = field(default_factory=dict)
    subpassos: list[Passo] = field(default_factory=list)
    certificado: Certificado | None = None

    def para_json(self) -> dict[str, Any]:
        return {
            "indice": self.indice, "tipo": self.tipo, "regra": self.regra,
            "antes": para_json(self.antes), "depois": para_json(self.depois),
            "operacao": self.operacao.para_json(), "relacao": self.relacao,
            "condicoes": [c.para_json() for c in self.condicoes],
            "justificativa": self.justificativa,
            "certificado": None if self.certificado is None else self.certificado.para_json(),
            "subpassos": [s.para_json() for s in self.subpassos],
        }

    @staticmethod
    def de_json(d: dict[str, Any]) -> Passo:
        return Passo(
            antes=de_json(d["antes"]), depois=de_json(d["depois"]),
            operacao=Operacao.de_json(d["operacao"]), relacao=d.get("relacao", "equivalente"),
            tipo=d.get("tipo", "algebra"), indice=d.get("indice", 0), regra=d.get("regra", ""),
            condicoes=tuple(Condicao.de_json(c) for c in d.get("condicoes", [])),
            justificativa=d.get("justificativa", {}),
            subpassos=[Passo.de_json(s) for s in d.get("subpassos", [])],
        )
