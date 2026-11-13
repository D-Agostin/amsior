# Gramática do LaTeX aceito pelo Amsior (fase 1A)

O analisador (`motor/amsior/expr/analisador.py`) é descendente recursivo e segue
a gramática abaixo. As regras marcadas com ★ dependem de contexto e por isso não
cabem numa gramática livre de contexto (ver `decisoes/0001`).

## Gramática

```
relacao    = expr [ ("=" | "<" | ">" | "\neq" | "\geq" | "\leq") expr ]
expr       = termo { ("+" | "-") termo }          (* associa à esquerda *)
termo      = ["-" | "+"] produto                  (* o menos engloba o produto *)
produto    = potencia { ["\cdot" | "\times" | "*" | "/"] potencia }
potencia   = atomo [ "^" grupo ]                  (* numa palavra, só a última letra *)
atomo      = numero | simbolo_ou_palavra | grupo | modulo | fracao | raiz
           | funcao | integral | "e^" grupo | "\mathrm{e}^" grupo
grupo      = "{" expr "}" | "(" expr ")" | "[" expr "]" | "\left(" expr "\right)"
modulo     = "|" expr "|" | "\left|" expr "\right|"
fracao     = "\frac{" ... "}{" ... "}"            (* ★ pode ser derivada *)
raiz       = "\sqrt" ["[" expr "]"] grupo
funcao     = ("\ln"|"\log"|"\exp"|"\sin"|"\cos"|"\tan") ["^" grupo] ["_" grupo] argumento
argumento  = grupo | potencia                     (* sem parênteses: um fator *)
integral   = "\int" ["_" grupo] ["^" grupo] corpo diferencial   (* ★ *)
```

## Regras de leitura

| Entrada | Leitura | Observação |
| --- | --- | --- |
| `a - b + c` | `Add(Sub(a, b), c)` | cadeias associam à esquerda |
| `-ab` | `Neg(Mul(a, b))` | |
| `a/bc` | `a / (b c)` | a palavra inteira vai para o denominador |
| `x^23` | `x² · 3` | sem chaves, o expoente é um caractere (como no LaTeX) |
| `2,5`, `2.5`, `2{,}5` | 2,5 | vírgula decimal; `;` separa argumentos |
| `P V` | `P · V` | espaço separa símbolos |
| `PV` ★ | pela tabela de símbolos | sem resolução única, o Amsior pergunta |
| `Re` ★ | `\mathrm{Re}` se `Re` está na tabela | |
| `\ln x y` | `ln(x) · y` | função sem parênteses age sobre um fator |
| `\ln xy` | `ln(x y)` | uma palavra conta como um fator |
| `\log x` | `log₁₀ x` | |
| `e^{x}`, `\exp(x)` | `Exp(x)` | `e` seguido de `^` é sempre a exponencial |
| `y(t)` ★ | `Func(y, t)` só se `y` tem papel de função | senão, `y · t` |
| `\frac{dy}{dt}` ★ | derivada | `d` colado no numerador e no denominador |
| `\frac{d y}{d t}` | divisão | com espaço, `d` é um símbolo |
| `\frac{d}{dt}(f)` | operador derivada aplicado a `f` | |
| `\left(\frac{\partial H}{\partial T}\right)_P` | derivada parcial com `P` mantido | |
| `\int f\,dx` ★ | o diferencial fecha o integrando | |
| `\int \frac{dP}{P}` ★ | `∫ (1/P) dP` | |
| `\int (a + dT^2)\,dT` | `d` dentro de parênteses não é diferencial | |

## Símbolos e índices

O `id` de um símbolo é a sua forma canônica, a mesma que o impressor emite.

| Entrada | Símbolo canônico |
| --- | --- |
| `T_1`, `T_{1}` | `T_{1}` |
| `\Delta H_{vap}`, `\Delta H_{\text{vap}}` | `\Delta H_{\mathrm{vap}}` (índice de várias letras fica em tipo reto) |
| `x_{\mathrm{A}}` | `x_{A}` |
| `C_{A0}`, `C_{p,m}` | iguais (índice misto fica como está) |
| `P^{sat}`, `P^{\mathrm{sat}}` | `P^{\mathrm{sat}}` (rótulo, não potência) |
| `H^{\circ}`, `y^{*}`, `B^{(0)}` | rótulos |
| `x^{n}`, `x^{2}` | potências |
| `\dot{m}`, `\dot m` | `\dot{m}` |
| `\overline{V}` | `\bar{V}` |
| `T'`, `T^{\prime}` | `T'` |
| `\Delta H` | `\Delta H`; `\Delta` precisa vir seguido de símbolo |

Para um rótulo numérico em sobrescrito use parênteses: `B^{(0)}`. Sem eles,
`B^{0}` é potência.

## Fora da v1 (recusado com mensagem)

`\sum`, `\pm`, `\tanh` e demais funções hiperbólicas, `\lim`, matrizes,
quebras de linha (`\\`) e alinhamentos (`&`).
