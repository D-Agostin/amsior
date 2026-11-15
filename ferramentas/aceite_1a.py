# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Relatório dos critérios de aceite da fase 1A (seção 10.1 da especificação).

1. Ida e volta LaTeX → árvore → LaTeX estável em 200 expressões.
2. Suíte "verificador sob ataque": reprova 100% dos passos errados e aprova
   100% dos certos.

Uso, a partir da pasta ``motor``: ``python ../ferramentas/aceite_1a.py``.
Sai com código 0 só se os dois critérios forem atendidos.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1] / "motor"
sys.path.insert(0, str(MOTOR))

from amsior.expr import analisar, para_latex  # noqa: E402
from amsior.units import carregar_glossario  # noqa: E402
from amsior.verify import certificar  # noqa: E402
from tests.conftest import tabela_corpus  # noqa: E402
from tests.corpus.corpus_latex import CORPUS  # noqa: E402
from tests.corpus.passos_ataque import CERTOS, ERRADOS, tabelas  # noqa: E402
from tests.corpus.test_ataque import montar  # noqa: E402


def criterio_ida_e_volta() -> tuple[bool, str]:
    estaveis = 0
    falhas: list[str] = []
    for latex, funcoes in CORPUS:
        tab = tabela_corpus(funcoes)
        try:
            arvore = analisar(latex, tab)
            canon = para_latex(arvore)
            if analisar(canon, tab) == arvore and para_latex(analisar(canon, tab)) == canon:
                estaveis += 1
            else:
                falhas.append(latex)
        except Exception as exc:  # o relatório lista qualquer falha
            falhas.append(f"{latex} ({type(exc).__name__})")
    ok = estaveis >= 200 and not falhas
    linha = f"{estaveis}/{len(CORPUS)} expressões estáveis (meta: 200)"
    return ok, linha + ("" if not falhas else "; falhas: " + "; ".join(falhas[:5]))


def criterio_ataque() -> tuple[bool, str]:
    g = carregar_glossario()
    tabs = tabelas(g)
    aprovados = sum(certificar(montar(c, tabs[c.tabela]), tabs[c.tabela], g).estado
                    == "aprovado" for c in CERTOS)
    reprovados = sum(certificar(montar(c, tabs[c.tabela]), tabs[c.tabela], g).estado
                     == "reprovado" for c in ERRADOS)
    ok = aprovados == len(CERTOS) and reprovados == len(ERRADOS)
    return ok, (f"certos aprovados {aprovados}/{len(CERTOS)}; "
                f"errados reprovados {reprovados}/{len(ERRADOS)}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    inicio = time.perf_counter()
    resultados = [("Ida e volta LaTeX", *criterio_ida_e_volta()),
                  ("Verificador sob ataque", *criterio_ataque())]
    print("Critérios de aceite da fase 1A")
    for nome, ok, detalhe in resultados:
        print(f"  [{'OK' if ok else 'FALHOU'}] {nome}: {detalhe}")
    print(f"  tempo: {time.perf_counter() - inicio:.1f} s")
    return 0 if all(ok for _, ok, _ in resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
