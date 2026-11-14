# 0003 — Verificador revisado (correções da revisão 0001)

- Data: 14/11/2026 (fim da fase 1A)
- Estado: aceita
- Substitui: partes da decisão 0002 (regras 3, 5 e 6)
- Origem: `docs/revisoes/0001-verificador-fase-1a.md`
- Especificação: v1.3 (seções 3.2, 5.1, 5.3 e 10.4)

## Decisões

1. **O verificador trabalha na árvore do Amsior.** A tabela de operações
   monta o resultado esperado em AmsiorExpr; o SymPy só entra na via
   simbólica. Assim o domínio de definição e a forma escrita não se perdem
   nas simplificações que o SymPy faz ao construir (`x/x → 1`).

2. **Obrigações de domínio** (`verify/dominio.py`). Cada nó parcial gera uma
   obrigação: denominador ≠ 0, argumento de ln e log > 0, radicando de raiz
   par ≥ 0, base de potência não inteira > 0, cos ≠ 0 na tangente, integrando
   definido no intervalo inteiro da integral. Comparando "antes" e "depois":
   - obrigação nova em "depois" (ou exigida pela operação) que não decorre das
     suposições, das condições declaradas nem do domínio de "antes": o passo
     reprova (`verif.condicao_ausente`) até a condição ser declarada;
   - obrigação de "antes" que não decorre do domínio de "depois": o passo
     alargou o domínio e a relação máxima é `implica`;
   - obrigação falsa com certeza (`ln(−u)` com `u > 0`): reprova
     (`verif.dominio_vazio`).
   V2 confere as obrigações da equação original no ponto da solução.

3. **Prova de obrigações sem `sympy.ask`** (`verify/logica.py`). A prova usa
   as suposições dos símbolos e fatos normalizados (`p/q > 0 ⇔ p·q > 0`,
   `ln x ≠ 0 ⇔ x − 1 ≠ 0`, fatores de algo não nulo são não nulos). O
   `sympy.ask` 1.14 responde `True` para "`−a > 0` dado `a ≠ 0`"; o
   verificador da 1A o usava como último recurso e foi retirado. O teste
   `test_sympy_ask_nao_e_confiavel` documenta o erro.

4. **Duas vias de identidade, sempre.** A via simbólica (SymPy) e a numérica
   (avaliador próprio em mpmath, `verify/avaliador.py`, que não passa pelo
   SymPy) rodam juntas. Se a simbólica prova e a numérica acha divergência, o
   passo reprova (`contraprova_divergente`). Uma diferença que simplifica a
   constante não nula reprova sem amostragem.

5. **Amostragem** (`verify/amostragem.py`):
   - magnitudes de 10⁻⁹ a 10⁹ em seis estratos (hipercubo latino em escala
     log), mais pontos perto dos números da expressão;
   - resíduo relativo sem piso: `|a − b| ≤ 10⁻³⁰·max(|a|, |b|)` mais o ruído
     de arredondamento medido entre 60, 120 e 240 dígitos;
   - cobertura de ramos: argumento de módulo e `w` em `√(w²)` precisam ser
     vistos com os dois sinais; uma varredura dirigida procura o que faltou;
   - pontos fora do domínio não entram na comparação (o domínio é decidido
     pelas obrigações), mas um ponto em que todas as obrigações valem e o
     avaliador não consegue o valor reprova (`dominio_inconsistente`).

6. **Objetos opacos.** Viram símbolos opacos, iguais dos dois lados:
   - derivada parcial com variáveis mantidas, `(∂H/∂T)_P` (também na conversão
     geral para o SymPy);
   - derivada de expressão com variável que não declara depender da variável
     de derivação (`dU/dT` com `U` sem dependência);
   - integral indefinida, até a fase 3A.

   Carregar o objeto sem mexer nele é verificável; "calculá-lo" não confere e
   gera `verif.dependencia_nao_declarada` ou `verif.integral_indefinida`.
   Símbolos de papel `parametro` e `constante` derivam para zero; símbolos sem
   papel declarado contam como variáveis.

7. **Integral definida calculada vira hipótese.** As variáveis do integrando
   que não declaram depender da variável de integração são tratadas como
   constantes, e isso aparece como hipótese ("T não varia com V" no trabalho
   isotérmico).

8. **Derivar ou integrar os dois lados** exige que a equação valha para todo
   valor da variável: ela envolve uma função dela (`y(x) = x²`), é uma
   identidade provada, ou o passo declara `operacao.identidade` (vira
   hipótese). Sem isso, `verif.equacao_nao_e_identidade`.

9. **Relação em dois eixos (A11).** `relacao` ∈ {`equivalente`, `implica`},
   sempre lida sob as hipóteses do passo. `restringe` deixa de existir; o
   verificador calcula `sob_hipotese` e lista as hipóteses usadas (condições,
   igualdade substituída, independência na integral, identidade declarada).
   O selo "Sob hipótese" as mostra. Substituição é sempre hipótese exibida até
   a fase 2 ligar a origem à ficha.

10. **Tabela de operações**: elevar a expoente 0 ou simbólico exige expoente
    ≠ 0 para equivalência; o índice de raiz é inteiro ≥ 2; a variável de
    derivação e de integração é um símbolo.

11. **Forma do passo**: desigualdades são recusadas
    (`verif.desigualdade_nao_suportada`); substituição recusa argumento que
    contém o próprio símbolo e símbolo que é variável ligada ou de
    dependência; condições sem nenhum ponto que as satisfaça reprovam;
    passos `principio` e `aproximacao` só com `contexto="ficha"`; qualquer
    exceção interna vira `verif.erro_interno`.

12. **Certificado auditável**: exigências e quem atendeu cada uma
    (suposição, condição, domínio de "antes" ou de "depois"), semente,
    pontos, pior resíduo, dígitos, ramos cobertos e não alcançados, versões do
    Amsior, do SymPy e do mpmath.

13. **Cadeia de passos** (`Verificador.certificar_cadeia`): continuidade
    ("depois" de um passo igual ao "antes" do seguinte), composição da relação
    (`implica` se algum passo for) e acúmulo das hipóteses. A conferência das
    candidatas por V2 quando a cadeia tem `implica` entra com o motor, na 1B.

## Limitações conhecidas

- Magnitudes fora de 10⁻⁹ a 10⁹ não são sorteadas: uma condição como
  `x > 10¹²` não encontra pontos e reprova o passo (falso negativo seguro).
- A varredura de ramos é dirigida, não exaustiva; ramo não alcançado fica
  registrado em `amostragem.ramos_nao_alcancados` no certificado.
- Valores grandes demais para calcular (`exp` de argumento acima de 10⁷,
  trigonométricas acima de 10²⁰) descartam o ponto.
- A existência do integrando no intervalo, em cada ponto sorteado, usa
  `solveset` e, sem resposta exata, varredura com detecção de troca de sinal.
- A prova de obrigações é incompleta por construção: o que ela não prova
  reprova ou rebaixa o passo, nunca aprova.
- Desigualdades, integral indefinida com constante e limite de tempo (T-06)
  continuam para as fases indicadas.
