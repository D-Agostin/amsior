# Amsior — Copyright (c) 2026 Ruan D'Agostin. SPDX-License-Identifier: AGPL-3.0-only
"""Biblioteca: esquema das fichas, vocabulários e ligações (seções 3.4, 3.5, 8.3 a 8.7)."""

from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

import pytest

from amsior.biblioteca import carregar_biblioteca
from amsior.biblioteca.esquema import tipos_sem_ficha
from amsior.rules.classificar import CHAVES
from amsior.units.glossario import pasta_biblioteca

BIB = pasta_biblioteca()


@pytest.fixture(scope="module")
def biblioteca():  # type: ignore[no-untyped-def]
    return carregar_biblioteca(BIB)


def test_biblioteca_do_repositorio_sem_problemas(biblioteca) -> None:  # type: ignore[no-untyped-def]
    assert [str(p) for p in biblioteca.problemas] == []


def test_listas_da_secao_8_7(biblioteca) -> None:  # type: ignore[no-untyped-def]
    mat = biblioteca.da_area("matematica")
    rea = biblioteca.da_area("reatores")
    assert len(mat) == 16 and len(rea) == 12
    assert [f.dados["ordem"] for f in mat] == list(range(1, 17))
    assert [f.dados["ordem"] for f in rea] == list(range(1, 13))
    assert mat[6].id == "matematica.equacao_racional"  # ficha-modelo
    assert rea[5].id == "reatores.cstr"  # ficha-modelo


def test_todo_tipo_de_equacao_leva_a_uma_ficha(biblioteca) -> None:  # type: ignore[no-untyped-def]
    """Critério da fase 2: toda etiqueta de tipo (D-12) leva a uma ficha de Matemática."""
    assert tipos_sem_ficha(biblioteca) == []
    for c in CHAVES:
        assert biblioteca.ficha_do_tipo(c).area == "matematica"  # type: ignore[union-attr]


def test_licenca_de_cada_arquivo() -> None:
    """D-16: conteúdo sob CC BY-SA 4.0; o glossário é parte do motor (AGPL-3.0)."""
    arquivos = sorted(BIB.rglob("*.yaml")) + sorted(BIB.rglob("*.svg"))
    assert any(a.suffix == ".svg" for a in arquivos)
    for arq in arquivos:
        cabecalho = "".join(arq.read_text(encoding="utf-8").splitlines(keepends=True)[:3])
        esperado = "AGPL-3.0-only" if arq.name == "_glossario.yaml" else "CC-BY-SA-4.0"
        assert f"SPDX-License-Identifier: {esperado}" in cabecalho, arq


def test_fontes_adaptaveis_tem_licenca_aberta(biblioteca) -> None:  # type: ignore[no-untyped-def]
    assert biblioteca.fontes["reamat_precalculo"].licenca == "CC-BY-SA-4.0"
    assert biblioteca.fontes["fogler"].uso == "citacao"
    # D-05: nada conferido de memória
    for f in biblioteca.fontes.values():
        assert f.dados.get("isbn") is None or (f.dados.get("conferido") or {}).get("por")


# ------------------------------------------------------------------ casos de erro


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    for nome in ("_fontes.yaml", "_hipoteses.yaml", "_glossario.yaml"):
        shutil.copy(BIB / nome, tmp_path / nome)
    (tmp_path / "matematica").mkdir()
    (tmp_path / "termodinamica").mkdir()
    return tmp_path


def _ficha(pasta: Path, caminho: str, texto: str) -> None:
    (pasta / caminho).write_text(textwrap.dedent(texto), encoding="utf-8")


def _problemas(pasta: Path) -> list[str]:
    return [str(p) for p in carregar_biblioteca(pasta).problemas]


CONCEITO = """\
    id: matematica.teste
    tipo: conceito
    versao: 1
    estado: {estado}
    area: matematica
    titulo: {{pt: "Teste"}}
    resumo: {resumo}
    secoes: {secoes}
    referencias: {referencias}
    revisao: {revisao}
    """


def _conceito(pasta: Path, **campos: str) -> list[str]:
    base = {"estado": "rascunho", "resumo": "null", "secoes": "[]",
            "referencias": "[{fonte: reamat_precalculo}]", "revisao": "null"}
    base.update(campos)
    _ficha(pasta, "matematica/teste.yaml", CONCEITO.format(**base))
    return _problemas(pasta)


def test_rascunho_minimo_e_valido(pasta: Path) -> None:
    assert _conceito(pasta) == []


def test_fora_de_rascunho_exige_conteudo(pasta: Path) -> None:
    p = _conceito(pasta, estado="auto_verificada")
    assert any("resumo: obrigatório" in x for x in p)
    assert any("secoes: pelo menos uma" in x for x in p)


def test_verificada_exige_conferencia_e_revisao(pasta: Path) -> None:
    p = _conceito(pasta, estado="verificada", resumo='[{texto: {pt: "R"}}]',
                  secoes='[{titulo: {pt: "A"}, blocos: [{texto: {pt: "B"}}]}]')
    assert any("conferido: obrigatório" in x for x in p)
    assert any("revisao.humana: obrigatória" in x for x in p)
    ok = _conceito(pasta, estado="verificada", resumo='[{texto: {pt: "R"}}]',
                   secoes='[{titulo: {pt: "A"}, blocos: [{texto: {pt: "B"}}]}]',
                   referencias='[{fonte: reamat_precalculo, conferido: {por: Ruan, em: 2026-11-15}}]',
                   revisao="{humana: {por: Ruan, em: 2026-11-15}}")
    assert ok == []


def test_campo_desconhecido_e_fonte_inexistente(pasta: Path) -> None:
    p = _conceito(pasta, referencias="[{fonte: livro_qualquer, pagnia: 3}]")
    assert any("fonte fora de _fontes.yaml" in x for x in p)
    assert any("campo desconhecido: pagnia" in x for x in p)


def test_numero_de_pagina_so_com_conferencia(pasta: Path) -> None:
    """D-05: número de página ou de equação não entra de memória."""
    p = _conceito(pasta, referencias="[{fonte: reamat_precalculo, pagina: 42}]")
    assert any("pagina: só preenchido junto com a conferência" in x for x in p)


def test_adaptacao_so_de_obra_aberta(pasta: Path) -> None:
    p = _conceito(pasta, referencias="[{fonte: fogler, uso: adaptacao}]")
    assert any("não tem licença que permita adaptar" in x for x in p)
    p = _conceito(pasta, estado="auto_verificada", resumo='[{texto: {pt: "R"}}]',
                  secoes='[{titulo: {pt: "A"}, blocos: [{texto: {pt: "B"}}]}]',
                  referencias="[{fonte: reamat_precalculo, uso: adaptacao}]")
    assert any("diga o que veio da obra" in x for x in p)


def test_arquivo_e_id_coincidem(pasta: Path) -> None:
    _ficha(pasta, "matematica/outro_nome.yaml", CONCEITO.format(
        estado="rascunho", resumo="null", secoes="[]", referencias="[]", revisao="null"))
    assert any("o arquivo tem de ser matematica/teste.yaml" in x for x in _problemas(pasta))


def test_tipo_explicado_por_duas_fichas(pasta: Path) -> None:
    for nome in ("a", "b"):
        _ficha(pasta, f"matematica/{nome}.yaml", f"""\
            id: matematica.{nome}
            tipo: conceito
            versao: 1
            estado: rascunho
            area: matematica
            titulo: {{pt: "{nome}"}}
            tipos: [tipo.racional]
            """)
    assert any("tipo.racional já é explicado por" in x for x in _problemas(pasta))


def test_ficha_visivel_nao_depende_de_rascunho(pasta: Path) -> None:
    _ficha(pasta, "matematica/rasc.yaml", """\
        id: matematica.rasc
        versao: 1
        estado: rascunho
        area: matematica
        titulo: {pt: "Rascunho"}
        """)
    p = _conceito(pasta, estado="auto_verificada", resumo='[{texto: {pt: "R"}}]',
                  secoes='[{titulo: {pt: "A"}, blocos: [{texto: {pt: "B"}}]}]')
    assert p == []
    texto = (pasta / "matematica/teste.yaml").read_text(encoding="utf-8")
    (pasta / "matematica/teste.yaml").write_text(texto + "equacoes: [matematica.rasc]\n", encoding="utf-8")
    assert any("ainda é rascunho" in x for x in _problemas(pasta))


EQUACAO = """\
    id: termodinamica.gas_ideal
    versao: 1
    estado: rascunho
    area: termodinamica
    titulo: {{pt: "Gás ideal"}}
    equacao: '{equacao}'
    variaveis:
      - {{simbolo: P, grandeza: pressao_absoluta}}
      - {{simbolo: V, grandeza: volume}}
      - {{simbolo: n, grandeza: quantidade_materia}}
      - {{simbolo: R, grandeza: constante_gases, constante: true}}
      - {{simbolo: T, grandeza: temperatura_absoluta}}
    hipoteses: [{hipoteses}]
    referencias: [{{fonte: svna}}]
    """


def _equacao(pasta: Path, equacao: str = "PV = nRT", hipoteses: str = "gas_ideal") -> list[str]:
    _ficha(pasta, "termodinamica/gas_ideal.yaml", EQUACAO.format(equacao=equacao, hipoteses=hipoteses))
    return _problemas(pasta)


def test_ficha_de_equacao_le_a_equacao_e_confere_simbolos(pasta: Path) -> None:
    glossario = (pasta / "_glossario.yaml").read_text(encoding="utf-8")
    for g in ("pressao_absoluta", "volume", "quantidade_materia", "constante_gases", "temperatura_absoluta"):
        assert f"\n  {g}:" in glossario, g
    assert _equacao(pasta) == []
    p = _equacao(pasta, "PV = nRT + Z")
    assert any("símbolo sem declaração em variaveis: Z" in x for x in p)
    p = _equacao(pasta, "PV = RT")
    assert any("declarado e ausente da equação: n" in x for x in p)
    p = _equacao(pasta, hipoteses="gas_perfeito")
    assert any("hipótese fora de _hipoteses.yaml: gas_perfeito" in x for x in p)


# ------------------------------------------------------------------ exemplos conferidos pelo motor


def test_exemplos_das_fichas_conferidos_pelo_motor(biblioteca) -> None:  # type: ignore[no-untyped-def]
    from amsior.biblioteca.exemplos import conferir_exemplos

    assert [str(p) for p in conferir_exemplos(biblioteca)] == []


def test_ficha_modelo_de_reatores(biblioteca) -> None:  # type: ignore[no-untyped-def]
    f = biblioteca.fichas["reatores.cstr"]
    assert f.visivel and f.dados["secoes"][0]["blocos"][0]["figura"] == "reatores/cstr_esquema.svg"
    assert len(f.dados["variaveis"]) >= 8
    titulos = [s["titulo"]["pt"] for s in f.dados["secoes"]]
    assert titulos == ["Como funciona", "Equação de projeto", "Onde se usa", "Vantagens e limitações"]


def test_figura_ausente_e_apontada(pasta: Path) -> None:
    p = _conceito(pasta, secoes='[{titulo: {pt: "A"}, blocos: [{figura: nada/sumiu.svg}]}]')
    assert any("figura ausente: figuras/nada/sumiu.svg" in x for x in p)


def test_ficha_modelo_de_matematica(biblioteca) -> None:  # type: ignore[no-untyped-def]
    f = biblioteca.fichas["matematica.equacao_racional"]
    assert f.visivel and f.estado == "auto_verificada"
    assert len(f.dados["secoes"]) >= 4 and len(f.dados["exemplos"]) >= 3
    assert biblioteca.ficha_do_tipo("tipo.racional") is f
    ref = f.dados["referencias"][0]
    assert ref["fonte"] == "reamat_precalculo" and ref["uso"] == "adaptacao"


def test_exemplo_com_resultado_errado_e_apontado(pasta: Path) -> None:
    from amsior.biblioteca.exemplos import conferir_exemplos

    _ficha(pasta, "matematica/teste.yaml", """\
        id: matematica.teste
        tipo: conceito
        versao: 1
        estado: rascunho
        area: matematica
        titulo: {pt: "Teste"}
        exemplos:
          - {enunciado: {pt: "a"}, equacao: 'x^2 - 2x - 8 = 0', pede: x, esperado: ['x = 4']}
          - {enunciado: {pt: "b"}, equacao: '2x = 6', pede: x, passos: false, esperado: ['x = 3']}
          - {enunciado: {pt: "c"}, equacao: '2x = 6', pede: x, esperado: ['x = 3']}
        """)
    b = carregar_biblioteca(pasta)
    assert b.problemas == []
    p = [str(x) for x in conferir_exemplos(b)]
    assert len(p) == 2
    assert "exemplos[0]" in p[0] and "esperados ['x = 4']" in p[0]
    assert "exemplos[1]" in p[1] and "agora tem passos" in p[1]


# ------------------------------------------------------------------ blocos (padrão de redação, seção 8.6)


@pytest.mark.parametrize(("bloco", "trecho"), [
    (r"{texto: {pt: 'Como \(x = 2\), segue'}}", "equação no texto corrido"),
    (r"{texto: {pt: 'vale \(a \leq b\)'}}", "equação no texto corrido"),
    (r"{lista: [{pt: 'com \(X \neq 1\)'}]}", "equação no texto corrido"),
    (r"{equacao: 'x = 2', nota: {pt: 'e \(y = 3\)'}}", "equação no texto corrido"),
    ("{equacao: 'x = 2', onde: [{simbolo: x}]}", "esperado {simbolo"),
    ("{texto: {pt: a}, equacao: x}", "exatamente um destes campos"),
    ("{passos: [{titulo: {pt: 'só um'}, blocos: [{texto: {pt: a}}]}]}", "pelo menos dois passos"),
    ("{caixa: aviso, blocos: [{texto: {pt: a}}]}", "tipo de caixa fora de"),
    ("{tabela: {colunas: [{pt: a}, {pt: b}], linhas: [[{pt: '1'}]]}}", "esperadas 2 células"),
])
def test_blocos_invalidos(pasta: Path, bloco: str, trecho: str) -> None:
    p = _conceito(pasta, secoes=f'[{{titulo: {{pt: "A"}}, blocos: [{bloco}]}}]')
    assert any(trecho in x for x in p), p


def test_simbolos_curtos_em_linha_sao_aceitos(pasta: Path) -> None:
    ok = _conceito(pasta, secoes=r"[{titulo: {pt: A}, blocos: [{texto: {pt: 'com \(\tau k\) e \(1/k\)'}}]}]")
    assert ok == []


def test_caixa_dentro_de_passo_e_recusada(pasta: Path) -> None:
    passos = ('{passos: [{titulo: {pt: "a"}, blocos: [{caixa: atencao, blocos: [{texto: {pt: "x"}}]}]},'
              ' {titulo: {pt: "b"}, blocos: [{texto: {pt: "y"}}]}]}')
    p = _conceito(pasta, secoes=f'[{{titulo: {{pt: "A"}}, blocos: [{passos}]}}]')
    assert any("caixa dentro de caixa ou de passo" in x for x in p)


def test_fichas_do_repositorio_sem_equacao_no_texto(biblioteca) -> None:  # type: ignore[no-untyped-def]
    """A regra vale para todo o conteúdo, inclusive enunciados de exemplos."""
    assert not [str(p) for p in biblioteca.problemas if "texto corrido" in p.mensagem]


# ------------------------------------------------------------------ exportação para a interface


def test_exportacao_so_leva_o_que_o_aluno_ve(biblioteca) -> None:  # type: ignore[no-untyped-def]
    import json

    from amsior.biblioteca.exportar import para_interface

    d = para_interface(biblioteca)
    json.dumps(d)
    assert set(d["fichas"]) == {f.id for f in biblioteca.fichas.values() if f.visivel}
    assert d["tipos"]["tipo.racional"] == "matematica.equacao_racional"
    assert all(fid in d["fichas"] for fid in d["tipos"].values())
    for f in d["fichas"].values():
        assert all(r in d["fichas"] for r in f["relacionadas"])
        for ex in f["exemplos"]:
            assert all(s["grandeza"] for s in ex["simbolos"])
    cstr = d["fichas"]["reatores.cstr"]
    fig = cstr["secoes"][0]["blocos"][0]
    assert fig["svg"].startswith("<svg") and "SPDX" not in fig["svg"]
    ref = cstr["referencias"][0]
    assert ref["titulo"].startswith("Elements") and ref["pagina"] is None and not ref["conferido"]
