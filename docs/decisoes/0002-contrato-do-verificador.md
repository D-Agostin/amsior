# 0002 — Contrato entre o passo e o verificador

- Data: 13/11/2026 (fase 1A)
- Estado: aceita; revisada em `docs/revisoes/0001-verificador-fase-1a.md` (correções pendentes)
- Detalha: especificação, seções 3.2, 4.1 e 5; para revisão do Fable ao fim da 1A

## Decisões

1. **Operação declarada no passo.** Além de `regra` (nome no catálogo do motor,
   fase 1B), todo passo traz `operacao`: nome, argumento, lado, símbolo e
   origem. O verificador refaz a operação pela sua própria tabela
   (`verify/operacoes.py`), sem consultar o catálogo de regras do motor.
2. **Duas classes de exigência.** `dominio` (dividir por zero, ln de não
   positivo): sem garantia, o passo é reprovado. `equivalencia` (multiplicar
   por algo que pode ser zero, elevar a potência par): sem garantia, a relação
   máxima é `implica`.
3. **Condição declarada que não decorre das suposições força `restringe`.**
   Dividir `(x - 1) z = x - 1` por `x - 1` com `x ≠ 1` declarado é válido, mas
   perde a solução `x = 1`; por isso a relação permitida é `restringe`.
4. **Identidade em duas rodadas.** Primeiro sem as condições declaradas; se só
   passar com elas, o passo precisou das condições (regra 3).
5. **Mudança de domínio reprova.** Na amostragem numérica, um ponto em que só
   um dos lados existe nos reais reprova o passo (por exemplo,
   `ln(x y) → ln x + ln y` com `x` e `y` reais quaisquer).
6. **Substituição é sempre, no máximo, `restringe` na fase 1A.** Sem a
   biblioteca não há como conferir se a igualdade substituída é uma definição
   ou uma hipótese. A fase 2 liga a origem à ficha citada e libera
   `equivalente` para definições conferidas.
7. **Zero tem qualquer dimensão.** `P V − n R T = 0` e `\int_0^T` são
   homogêneos.
8. **Relações `Lt` e `Le`** entram na árvore ao lado de `Ne`, `Gt` e `Ge`,
   porque o usuário digita `<` e `≤`.

## Limitações conhecidas (para a revisão)

- A identidade numérica sorteia magnitudes entre 10⁻² e 10²; uma condição como
  `x > 1000` não encontra pontos e reprova o passo (falso negativo seguro).
- Integrais indefinidas são comparadas sem constante de integração; avaliar
  uma integral indefinida com `+ C` fica para a fase 3A.
- Derivar em relação a uma variável da qual o símbolo não declara dependência
  dá zero, de forma consistente; o aviso ao usuário (seção 4.3) é da fase 1B.
- Não há limite de tempo dentro do verificador; ele vem do processo de
  trabalho (T-06), que é da fase 1B.
- As mensagens mostram a forma esperada na ordem do SymPy (`\frac{R T n}{V}`),
  não na ordem do autor.
