# 0001 — Analisador descendente recursivo próprio em vez de Lark

- Data: 13/11/2026 (fase 1A)
- Estado: aceita
- Altera: especificação, seções 2 e 3.1 (que previam a biblioteca Lark)

## Contexto

A especificação previa converter o LaTeX restrito com uma gramática Lark. Ao
implementar, quatro regras centrais se mostraram dependentes de contexto:

1. Palavras como `PV` só se resolvem consultando a tabela de símbolos da folha.
2. Dentro de uma integral, `dx` ou `\mathrm{d}x` fecha o integrando, mas só no
   nível do corpo (não dentro de parênteses).
3. `\frac{dy}{dt}` é derivada apenas quando numerador e denominador seguem o
   padrão de diferencial; `\frac{d}{t}` e `\frac{d y}{d t}` são divisões.
4. `y(t)` é aplicação de função só se `y` tem papel de função na tabela.

Uma gramática livre de contexto exigiria pós-processamento para cada uma
dessas regras, espalhando a lógica entre a gramática e o código.

## Decisão

Analisador descendente recursivo escrito à mão (`amsior/expr/analisador.py`),
com a gramática documentada em `docs/gramatica.md`. A dependência Lark sai da
pilha.

## Consequências

- Mensagens de erro em português, com posição, para cada regra.
- Uma dependência a menos para empacotar.
- A garantia de correção vem dos testes: corpus de 232 expressões de
  engenharia química com leitura conferida, testes de unidade por regra e um
  teste de propriedade que exige ida e volta exata em 6.000 árvores aleatórias.
  Esse teste achou dois erros reais durante a fase 1A, já corrigidos.
