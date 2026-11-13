# Amsior

Calculadora sofisticada e biblioteca didática de equações para engenharia química.
Cada cálculo mostra o raciocínio, e nenhum passo aparece sem ter sido verificado
por máquina.

> Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
> Veja [LICENSE](LICENSE).

## Estado: fase 1A (fundação) concluída

| Critério de aceite (especificação, seção 10.1) | Resultado |
| --- | --- |
| Ida e volta LaTeX → árvore → LaTeX estável em 200 expressões | 232/232 |
| Verificador sob ataque: aprova 100% dos passos certos | 41/41 |
| Verificador sob ataque: reprova 100% dos passos errados | 35/35 |

Rode o relatório com `python ../ferramentas/aceite_1a.py` a partir da pasta `motor`.

## O que existe

- `motor/amsior/expr`: árvore de expressões (AmsiorExpr), analisador do LaTeX restrito,
  impressão canônica, JSON e ponte com o SymPy.
- `motor/amsior/units`: glossário de grandezas, análise dimensional simbólica (V5) e
  conversão de unidades ciente de temperatura absoluta e diferença.
- `motor/amsior/verify`: certificação de passos (V1 e V5), verificação de solução (V2) e
  a tabela própria de operações do verificador.
- `motor/amsior/i18n`: catálogo de textos (pt-BR agora, en depois).
- `biblioteca/_glossario.yaml`: 60 grandezas com unidade SI e suposições.
- `ferramentas/empacotamento`: protótipo "olá, mundo" do instalador (PyInstaller).

## Como rodar

Veja [docs/instalar-python-windows.md](docs/instalar-python-windows.md). Em resumo:

```
cd motor
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
python -m mypy
python -m pytest
```

## Documentos

- [Especificação da fase 0](docs/especificacao.md)
- [Gramática do LaTeX aceito](docs/gramatica.md)
- [Registros de decisão](docs/decisoes/)
