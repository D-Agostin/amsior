# 0004 — Motor de isolar (fase 1B)

- Data: 14/11/2026
- Estado: aceita
- Detalha: especificação, seções 2 e 4.2

## Decisões

1. **Ordem de dependência.** `verify` passa a vir antes de `rules` e `steps`.
   O motor chama o verificador a cada passo e só entrega o que foi
   certificado (T-02); o verificador continua sem conhecer o motor, que é o
   que garante a independência dele.

2. **Uma regra por forma** (`rules/isolar.py`): soma, subtração, oposto,
   produto, quociente, potência (inteira, não inteira, alvo no expoente),
   exponencial, logaritmo natural e em outra base, raiz e módulo. Cada regra
   propõe o passo, a operação que o verificador refaz, as condições que as
   suposições não garantem e a justificativa (chave do catálogo).

3. **Operação e acabamento em passos separados.** Dividir por `P` mostra
   `PV/P = nRT/P`; o passo seguinte cancela e junta frações
   (`rules/simplificar.py`). No modo resumido os dois se fundem
   (`fundivel`). O acabamento só reorganiza: achata frações de frações, põe
   números e símbolos antes de funções e somas e nunca expande.

4. **Ramos.** Raiz par e módulo abrem dois ramos, cada um sob a sua
   hipótese. Um ramo excluído pelas suposições (pressão positiva descarta a
   raiz negativa) é descartado com motivo.

5. **Várias ocorrências.** O alvo vai todo para a esquerda, denominadores com
   o alvo são eliminados e, se a expressão for linear no alvo, ela é
   agrupada (coeficiente por derivada, sem expandir logaritmos) e dividida.
   Quadráticas e formas transcendentais caem no oráculo.

6. **Domínio à vista.** Quando um passo apaga uma obrigação de domínio
   (`a/x · x = a`), o motor declara a condição (`x ≠ 0`), que aparece como
   hipótese.

7. **Validade do resultado.** Se o V2 só aprova o resultado com condições a
   mais (`L = μv/τ` exige `v ≠ 0`), elas viram a validade do ramo, exibida
   ao aluno, e o V2 roda de novo com elas.

8. **Falha.** Qualquer passo reprovado descarta a resolução inteira; sobra o
   resultado do oráculo, rotulado "sem passos", só se passar em V2. O passo
   reprovado fica em `rejeitados`, para virar teste de regressão.

## Mudanças no verificador feitas junto

- V2 usa o domínio do problema (obrigações da equação que não envolvem o
  alvo) como fato, substitui a solução nas condições do ramo e devolve as
  condições que faltam.
- Nas soluções do "depois" um lado pode ser trocado pelo outro nas
  obrigações de "antes" (`C_{A0}/C_A = e^{kt}` garante `C_{A0}/C_A > 0`).
- Absorção numérica (`e^{−X}(T_i − T_∞) + T_∞ − T_∞` com `T_∞` grande)
  descarta o ponto, como o estouro.

## Corpus

`tests/corpus/corpus_isolar.py`: 64 equações das sete áreas, 279 variáveis.
Todas isolam com passos certificados, salvo as declaradas não isoláveis
(LMTD em ΔT₁ e ΔT₂, Fenske em x_D e x_B). Van der Waals e Antoine entram
com as fichas da fase 2, quando suas constantes tiverem grandeza.
