# Revisão 0001 — Desenho do verificador (fase 1A)

- Data: 14/11/2026
- Revisor: Fable 5.2 (não participou da construção)
- Objeto: `motor/amsior/verify/`, `expr/ponte_sympy.py`, `units/homogeneidade.py`,
  decisão 0002 e seções 3.2 e 5 da especificação, no commit `e22c20a`
- Método: leitura do código e tentativa de construir passos errados que o
  verificador aprove
- Evidência: `motor/tests/corpus/test_revisao_fable.py` (35 casos, todos
  reproduzem a falha)

## Parecer

**A arquitetura está certa e deve ser mantida. O verificador ainda não pode
certificar passos de cálculo nem ser a única barreira de domínio.** Antes da
fase 1B ele precisa das correções A1 a A10 abaixo.

O que está bem resolvido:

- o verificador refaz a operação pela própria tabela, sem consultar o motor;
- relação ou condição mais otimista que a tabela reprova o passo;
- a identidade roda em duas rodadas, e a que depende de condição rebaixa a relação;
- na amostragem, um ponto em que só um lado existe reprova o passo;
- inconclusivo equivale a reprovado, e a semente é reprodutível;
- substituição é conservadora enquanto não há biblioteca.

A suíte de ataque da 1A (35 errados reprovados) mede bem os erros algébricos
clássicos: sinal, lado esquecido, raiz perdida, logaritmo de soma. Ela não
cobria as classes abaixo.

## Achados que aprovam matemática falsa

Gravidade alta: o passo errado recebe selo "Verificado".

### A1. A variável mantida constante é descartada

`PDeriv.mantidas` existe na árvore, mas `ponte_sympy` converte toda derivada
parcial em `Derivative(f, x)`. Para o verificador, `(∂H/∂T)_P` e `(∂H/∂T)_V`
são o mesmo objeto.

- Aprovado hoje: reescrever `(∂H/∂T)_P = nR` como `(∂H/∂T)_V = nR`, isto é,
  `C_p = C_v`.
- Efeito: nenhuma demonstração de termodinâmica com derivadas parciais (relações
  de Maxwell, `C_p − C_v`, Joule-Thomson) pode ser certificada.
- Correção: a derivada parcial vira um objeto opaco identificado por
  (função, variável, conjunto mantido). O verificador só a manipula por regras
  nomeadas (regra da cadeia, regra cíclica, inversão), nunca por `doit()`.

### A2. Símbolo sem dependência declarada é tratado como constante

`Derivative(U, T)` com `U` símbolo simples vale zero no SymPy.

- Aprovado hoje: derivar `PV = nRT` em `T` e obter `0 = nR`; reescrever
  `dU/dT = nR` como `0 = nR`.
- A decisão 0002 listou isto como aviso de interface para a 1B. É falha de
  correção: o verificador certifica uma falsidade.
- Correção: derivar um símbolo de papel `variavel` em relação a outra variável
  sem dependência declarada reprova o passo ("dependência não declarada"). Só
  `parametro` e `constante` derivam para zero.

### A3. Derivar ou integrar os dois lados de uma equação qualquer

`derivar_ambos` e `integrar_ambos` devolvem `implica` para qualquer equação.
Isso só vale quando a equação é uma identidade na variável (vale para todo
valor dela), não uma equação a resolver.

- Aprovado hoje: `x² = 4 ⇒ 2x = 0`; `dy/dx = 2x ⇒ y = x²`, sem constante.
- Correção: as duas operações exigem que o passo declare a equação como
  identidade na variável, e essa declaração entra como hipótese exibida.
  Integração indefinida exige a constante explícita (símbolo de papel
  "constante de integração") ou fica `pendente` até a fase 3A; não pode sair
  aprovada sem ela.

### A4. A amostragem só cobre módulos entre 0,01 e 100

Qualquer expressão com ramos (`|·|`, raiz de quadrado) cuja troca de ramo fique
fora dessa faixa é aprovada no ramo errado.

- Aprovado hoje: `|Re − 2300| → 2300 − Re`; `√((u − 300)²) → 300 − u`.
- Em engenharia química as grandezas passam de 100 o tempo todo (temperatura
  em K, pressão em Pa, Re).
- Correção, as duas juntas:
  1. sortear por estratos de magnitude, de 10⁻⁹ a 10⁹;
  2. exigir cobertura de ramos: para cada subexpressão sensível a sinal
     (argumento de `Abs`, radicando de raiz par, base de potência não inteira),
     a amostra precisa conter os dois sinais quando ambos são possíveis. Sem
     isso, o resultado é inconclusivo e reprova.

### A5. O resíduo é dividido por max(|a|, |b|, 1)

O piso 1 transforma o teste relativo em absoluto para valores pequenos.

- Aprovado hoje: `6,626·10⁻³⁴ u → 13,252·10⁻³⁴ u` (constante de Planck
  dobrada); `10⁻³³(u − v) → 10⁻³³(u + v)`; `x = z → x = z + 10⁻³¹`.
- Correção: resíduo relativo sem piso, `|a − b| / max(|a|, |b|)`, com os dois
  nulos contando como iguais. O cancelamento numérico passa a gerar falso
  negativo, que é o lado seguro.

### A6. A via simbólica não conhece o domínio de definição

É o achado mais amplo. O SymPy cancela e avalia na construção (`x/x → 1`,
`exp(ln x) → x`, `ln(−u) → ln u + iπ`, `√(−u)·√(−u) → −u`). A via simbólica
compara o que sobrou, e a checagem de domínio só existe na via numérica.

- Aprovados hoje como equivalência:
  - cancelar `(x − 1)` de numerador e denominador, e o inverso;
  - `tg x · cos x → sen x`;
  - `exp(ln x) → x` e `(√x)² → x` com `x` real;
  - `ln(−u) − ln(−v) → ln u − ln v` com `u, v > 0` (o "antes" nem existe nos reais);
  - somar `1/x` aos dois lados de `x = 0`;
  - multiplicar `x² = x` por `1/x` declarando `implica` (perde `x = 0`);
  - `∫ₐᵇ dx/x²` com `a < 0 < b` (integral divergente).
- A camada V2 tem o mesmo defeito: aceita `x = 1` como solução de
  `(x − 1)(x + 1)/(x − 1) = 2` e `x = −3` como solução de `exp(ln x) = −3`.
- Correção: um módulo de obrigações de domínio calculado na árvore AmsiorExpr,
  antes da conversão ao SymPy. Ele percorre "antes", "depois" e o argumento da
  operação e coleta:
  - denominador ≠ 0;
  - argumento de ln e log > 0;
  - radicando de raiz par ≥ 0;
  - base de potência não inteira > 0;
  - integrando definido em todo o intervalo.

  Regras:
  - obrigação de "depois" que não decorre das suposições, das condições nem das
    obrigações de "antes": o passo restringiu o domínio e só pode ser
    `restringe`, com a condição exibida;
  - obrigação de "antes" que some em "depois": o passo alargou o domínio e só
    pode ser `implica`;
  - obrigação violada com certeza (`ln(−u)`, `u > 0`): reprova;
  - V2 confere as obrigações da equação original no ponto da solução.

### A7. Lacunas na tabela de operações

- `elevar_ambos` com expoente 0 aprova `u = v ⇔ 1 = 1`. Com expoente simbólico
  `a` aprova `u = v ⇔ uᵃ = vᵃ`, falso quando `a = 0`. Falta a exigência de
  equivalência "expoente ≠ 0".
- `raiz_ambos` aceita índice simbólico, zero ou negativo. O índice deve ser
  inteiro ≥ 2.

### A8. Desigualdades são aceitas por acidente

`reescrever` sobre `x > 100 → x > 150` cai na amostragem, que compara
verdadeiro/falso como 1/0. Fora da faixa sorteada os dois dão "falso" e o passo
é aprovado. O verificador não tem regras para desigualdades e deve recusá-las
("passo sem equação") até que tenha.

## Achados de robustez e de modelo

Gravidade média.

### A9. Substituição e condições sem conferência mínima

- `substituir x := x + 1` é aprovado como `restringe`. A substituição deve
  recusar argumento que contenha o próprio símbolo.
- Condições contraditórias (`x > 1` e `x < 0`) são aceitas e aprovam uma
  divisão como `restringe`. Antes de usar o conjunto de condições, o
  verificador deve encontrar ao menos um ponto que satisfaça todas elas e as
  suposições.

### A10. Exceção em vez de reprovação

Derivar em relação a um número e substituir a variável de uma derivada levantam
`ValueError`. `certificar` nunca deve levantar: qualquer exceção interna vira
`reprovado` com motivo `verif.erro_interno`, e a entrada vai para o registro de
regressão.

### A11. As três relações misturam dois eixos

`equivalente`, `implica` e `restringe` são tratadas como uma escada, mas
`implica` (antes ⇒ depois, pode criar raízes) e `restringe` (depois ⇒ antes sob
condição nova, pode perder raízes) não são comparáveis. Hoje um passo que
depende de condição aceita também `implica`, o que só é verdade dentro da
hipótese.

Proposta: separar direção e condicionalidade.

- `relacao` ∈ {`equivalente`, `implica`}, sempre lida sob as condições do passo;
- as condições novas ficam em `condicoes` com origem `hipotese` e produzem o
  selo "Sob hipótese";
- `restringe` passa a ser um nome de exibição para "equivalente sob hipótese
  nova".

Isso dá uma regra de composição simples para a cadeia (A12) e exige a v1.3 da
especificação (seção 3.2).

### A12. Não existe verificação da cadeia

Cada passo é julgado isoladamente. Falta, e deve entrar na 1B junto com o motor:

- continuidade: o "depois" do passo i é estruturalmente o "antes" do passo i+1;
- composição: a relação do conjunto é a mais fraca da cadeia, e as hipóteses se
  acumulam;
- conclusão: o resultado só é exibido como "solução" se a cadeia for
  equivalente sob as hipóteses acumuladas; se houver `implica`, V2 confere cada
  candidata (raízes estranhas).

### A13. Independência parcial entre motor e verificador

Os dois usarão a mesma `ponte_sympy` e o mesmo SymPy. Um erro de conversão
(A1 é um exemplo) engana os dois ao mesmo tempo.

Proposta:

- rodar a amostragem numérica sempre, inclusive quando a via simbólica aprova,
  como contraprova;
- avaliar a amostragem por um avaliador próprio da árvore AmsiorExpr em mpmath,
  sem passar pelo SymPy.

O custo é pequeno e as duas vias passam a ser de fato independentes.

### A14. Tipo `principio` declarado pelo próprio passo

Um passo que se declare `principio` ou `aproximacao` escapa de V1 e fica
`pendente`. O verificador deve aceitar esses tipos apenas de fichas curadas
(origem conferida), nunca de passos gerados pelo motor.

### A15. Certificado pouco auditável

O certificado aprovado não registra o que foi provado. Deve guardar:

- as exigências e como cada uma foi satisfeita (suposição, condição, prova);
- a semente, o número de pontos e o pior resíduo;
- as versões do SymPy e do mpmath.

O selo "Sob hipótese" depende desse registro.

## Observações menores

- `0⁰` é tratado como 1 pelo SymPy e como "qualquer dimensão" por V5.
- `∫₀ᵇ dx/(1 − x) → −ln(1 − b)` é aprovado sem exigir `b < 1`; A6 resolve.
- O limite de tempo (T-06) continua pendente para a 1B, como previsto.

## Ordem de correção recomendada

1. A6 (obrigações de domínio) e A13 (avaliador próprio): mudam a estrutura e as
   demais correções se apoiam neles.
2. A4 e A5 (amostragem).
3. A1, A2 e A3 (cálculo).
4. A7 a A10 (tabela e robustez).
5. A11, com a v1.3 da especificação, e A12 na abertura da 1B.
6. A14 e A15.

Critério de aceite da correção: os 35 casos de `test_revisao_fable.py` passam a
ser reprovados (retirar as marcas `xfail`), os 41 passos certos da suíte de
ataque continuam aprovados, e o teste de propriedade ganha geradores para
ramos, polos e escalas extremas.
