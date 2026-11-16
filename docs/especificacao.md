# Amsior — Especificação de Arquitetura (Fase 0)

13/11/2026 · v1.7 em 15/11/2026

O Amsior foi idealizado por Ruan D'Agostin como ferramenta livre para fomento à ciência e à engenharia, com fins educacionais e gratuitos.

Esta especificação fecha a arquitetura do Amsior v1: uma aplicação web que roda inteira no navegador, sem instalação e sem servidor de cálculo, com motor em Python (via WebAssembly) e interface em React, organizada como folha de cálculo, em que todo passo exibido é verificado por máquina antes de aparecer. As fases 1 a 4 seguem este documento como roteiro; mudar uma decisão daqui exige registrar a mudança na seção 10.

## 1. Decisões fechadas e escopo da v1

As decisões abaixo foram tomadas por Ruan em 13/11/2026 e orientam todo o resto.

| ID | Tema | Decisão |
| --- | --- | --- |
| D-01 | Público | Alunos e professores de engenharia química; uso didático |
| D-02 | Plataforma | Aplicação web que roda inteira no navegador do usuário: sem instalação, sem conta e sem servidor de cálculo; funciona sem internet depois da primeira visita. Revista em 15/11/2026 (D-14); até então era um aplicativo local para Windows |
| D-03 | Formato de trabalho | Folha de cálculo (várias equações, textos e tabelas encadeados, variáveis compartilhadas) |
| D-04 | Motor de passos v1 | Isolar variável; integrais e derivadas; EDOs de 1ª ordem (separáveis e lineares) |
| D-05 | Citações | Ficha nasce com livro, capítulo e seção; número de equação e página só entram após conferência de Ruan na última edição da fonte (D-09) |
| D-06 | Notação | Livro-base por área, glossário único de grandezas, trabalho pela convenção IUPAC (ΔU = Q + W) |
| D-07 | Idioma | Português do Brasil com vírgula decimal; textos separados do código para tradução futura |
| D-08 | Aprovação de fichas | Verificação automática obrigatória + revisão de Ruan; revisor externo opcional |

Duas decisões foram acrescentadas por Ruan no mesmo dia, depois da primeira versão:

| ID | Tema | Decisão |
| --- | --- | --- |
| D-09 | Edições | A referência é sempre a última edição de cada fonte (seção 8.1); edição nova reabre a conferência das citações |
| D-10 | Propriedades dos livros | Biblioteca própria de propriedades físicas e químicas transcritas dos livros, separada da de equações, com uso opcional (seção 7.5) |

Uma decisão foi acrescentada por Ruan em 14/11/2026, na abertura da fase 1B:

| ID | Tema | Decisão |
| --- | --- | --- |
| D-11 | Design visual | O design é requisito, não acabamento: um visual excelente cansa menos e favorece a aprendizagem, e é onde os softwares da área costumam falhar. Modos claro e escuro com o mesmo cuidado (seção 9.4); nenhuma tela entra numa versão sem a revisão visual de Ruan nos dois modos |
| D-12 | Tipo da expressão | Toda equação mostra, para a variável escolhida, o tipo de equação que ela é (1º grau, racional, irracional, exponencial, logarítmica, mista...), com ligação para a ficha de Matemática que explica o tipo (seção 4.7) |
| D-13 | Fichas de conceito | A biblioteca ganha fichas de conceito, além das de equação: texto didático, ilustrações e animações sobre um assunto. Duas seções nascem com elas: Matemática (tipos de expressão e de equação, domínio, equivalência) e Reatores (cada tipo de reator, como funciona, usos e animações de demonstração). Seções 3.5, 8.1 e 8.7 |

Duas decisões foram acrescentadas por Ruan em 15/11/2026, depois do primeiro executável (decisão 0006 do repositório):

| ID | Tema | Decisão |
| --- | --- | --- |
| D-14 | Navegador | O Amsior passa a rodar no navegador (D-02 revista). Motivo: o Controle Inteligente de Aplicativos do Windows bloqueia executáveis sem assinatura digital e não oferece exceção ao usuário; assinar custa dinheiro ou depende de terceiros, e um site não precisa de assinatura, funciona em qualquer sistema e não exige instalação. O executável da fase 1B deixa de ser entregue |
| D-15 | Software livre | Código público sob a licença AGPL-3.0, de uso gratuito. O projeto não aceita contribuições externas por enquanto (pull requests fechados); relatos de erro são bem-vindos |

### Decisões técnicas derivadas

Estas decorrem das decisões acima e ficam fechadas por esta especificação.

| ID | Decisão | Motivo |
| --- | --- | --- |
| T-01 | A forma das expressões é guardada em árvore própria (AmsiorExpr); o SymPy atua só como oráculo | O SymPy reordena e simplifica sozinho, o que destrói a forma didática do passo |
| T-02 | Nenhum passo é exibido sem certificado de verificação | Conformidade científica (seção 5) |
| T-03 | Demonstrações da biblioteca são redigidas e curadas; passos de equações do usuário são gerados | O motor não inventa física; hipóteses e aproximações exigem revisão humana |
| T-04 | Água pela formulação IAPWS-95 (padrão do CoolProp); IAPWS-IF97 disponível como opção | Corrige o resumo, que citava só a IF97: a IAPWS-95 é a formulação científica de referência, a IF97 é a industrial |
| T-05 | Arquivos nunca passam por `eval` nem por `sympify` de texto | Segurança: uma folha recebida de terceiros não pode executar código |
| T-06 | Todo cálculo roda fora da linha de execução da interface (num Web Worker), com tempo limite; ao estourar, o trabalhador é encerrado e reposto | O SymPy pode travar em expressões difíceis; a interface nunca congela |
| T-07 | Nada do que o usuário digita sai do navegador: sem contas, sem telemetria e sem pedidos de rede depois de carregados os arquivos da aplicação | Decorre de D-02 (não há servidor de cálculo) e protege o aluno; folhas ficam no dispositivo dele |

### Fora do escopo da v1

- Solução numérica passo a passo de equações implícitas e sistemas (cúbicas de estado em V, Colebrook, Rachford-Rice). A v1 identifica o caso e informa que não há forma fechada elementar; a solução numérica entra na v1.1.
- EDOs de 2ª ordem geradas pelo motor (a equação da aleta aparece na biblioteca como demonstração curada).
- Misturas com equações de estado, simulação de fluxogramas e otimização.
- Colaboração em rede e contas de usuário.
- Aplicativo de desktop com instalador (D-14). Se um dia voltar, precisa de assinatura digital de código.

## 2. Arquitetura geral

O Amsior é um site estático: o navegador baixa a interface e o motor, e tudo roda no dispositivo do usuário. O motor é o mesmo pacote Python `amsior`, executado pelo Pyodide (CPython compilado para WebAssembly) dentro de um Web Worker. A interface nunca faz matemática: ela edita, exibe e pede.

```
Interface (página): folha, tabela de variáveis, biblioteca, MathLive e KaTeX
        ^ mensagens JSON {id, rota, dados}  (mesmo contrato da seção 9.2)
        v
Trabalhador de cálculo (Web Worker com Pyodide, encerrado e reposto ao estourar o tempo):
    api (despacho)  -->  steps + rules  -->  verify  |  units + numerics  |  props + interp
    por baixo: SymPy, mpmath, pint (e, na fase 3B, as bibliotecas de propriedades)

Armazenamento do navegador: folhas e preferências     Arquivos .amsior: abrir e baixar pelo usuário
Service worker: guarda os arquivos da aplicação para uso sem internet
Hospedagem: arquivos estáticos (GitHub Pages), publicados pela integração contínua
```

O módulo em destaque é o verificador: nada gerado pelo motor de passos volta à interface sem passar por ele.

### Partes em execução

1. **Página** (React): mostra a interface e guarda o estado da folha. Pode ser instalada como aplicativo pelo próprio navegador (PWA), com janela própria.
2. **Trabalhador de cálculo** (Web Worker): carrega o Pyodide e o pacote `amsior` uma vez e responde aos pedidos. Cada pedido tem limite de tempo, contado a partir de quando começa a rodar (padrão 30 s, provisório até a medição em computadores de aluno; decisão 0006); ao estourar, a página encerra o trabalhador, cria outro e mostra um erro explicado (T-06). Pedidos repetidos de análise substituem o que ainda espera na fila.
3. **Service worker**: guarda em cache a interface, o Pyodide e o motor, cada arquivo identificado pelo hash do seu conteúdo. Ele se registra só depois de o motor ficar pronto, para a cópia sair do cache do navegador e a primeira visita não baixar tudo duas vezes. Depois da primeira visita o Amsior abre sem internet. Versão nova é baixada em segundo plano, aproveitando os arquivos que não mudaram; a barra de estado avisa e o botão "Atualizar" a põe em uso (senão, ela entra na abertura seguinte).
4. **Partida sem espera**: textos e glossário vêm prontos do site (`motor/dados.json`, gerados na montagem pelas mesmas rotas do motor); a tela abre na hora e os pedidos esperam o motor na fila, com o estado na barra inferior.

Não há servidor de aplicação: a hospedagem só entrega arquivos. O servidor local da fase 1B (`amsior.api.app`, `amsior.janela`) continua existindo como modo de desenvolvimento e como referência dos testes: o mesmo pedido tem de dar a mesma resposta no Python nativo e no navegador.

### Módulos do pacote `amsior`

| Módulo | Responsabilidade | Depende de |
| --- | --- | --- |
| `expr` | Árvore AmsiorExpr, analisador de LaTeX restrito, conversão para LaTeX e SymPy, símbolos e suposições | SymPy |
| `units` | Dimensões, conversão, homogeneidade dimensional, tipos de temperatura e pressão | `expr`, pint |
| `verify` | Certificados por passo e verificações de ponta a ponta | `expr`, `units`, SymPy, mpmath |
| `rules` | Catálogo de regras de transformação, cada uma com justificativa e condições | `expr`, `verify` (modelo do passo e provas de suposição) |
| `steps` | Estratégias: isolar, integrar, derivar, resolver EDO; produz a lista de passos e só a entrega certificada | `rules`, `units`, `verify` |
| `numerics` | Avaliação numérica, algarismos significativos, formatação pt-BR | `expr`, `units` |
| `props` | Propriedades de fluidos puros e correlações com faixa de validade; pacotes de propriedades dos livros (subpacote props.livros) | `units`, CoolProp, chemicals |
| `interp` | Interpolação linear, bilinear e spline com passos e avisos | `numerics` |
| `library` | Carga e validação das fichas, glossário de grandezas, vocabulário de hipóteses | `expr`, `units`, `verify` |
| `sheet` | Modelo da folha, grafo de dependências, recálculo, leitura e gravação de `.amsior` | todos os anteriores |
| `i18n` | Catálogo de textos e modelos de justificativa por idioma | nenhum |
| `api` | Despacho dos pedidos (`executar(rota, dados)`), esquemas de entrada e saída. No navegador é chamado pelo trabalhador; o servidor HTTP local fica só para desenvolvimento | todos |

Regra de dependência: cada módulo só depende dos que estão acima dele na tabela. `steps` não conhece `sheet` nem `api`; `verify` não conhece `rules` nem `steps` (ele recebe passos prontos e os julga de forma independente). O motor chama o verificador para entregar só passos certificados (decisão 0004).

### Pilha tecnológica

| Camada | Escolha | Observação |
| --- | --- | --- |
| Linguagem do motor | Python 3.12 ou superior | Tipagem estrita (mypy); só bibliotecas que rodam no Pyodide |
| Python no navegador | Pyodide (CPython em WebAssembly), dentro de um Web Worker | Versão travada; SymPy, mpmath e pint nas mesmas versões do arquivo de trava do motor |
| Álgebra simbólica | SymPy | Oráculo; precisão arbitrária via mpmath |
| Unidades | pint | Um único registro, definido em `units` |
| Propriedades | CoolProp; chemicals/thermo para correlações | Seção 7. Funcionamento no Pyodide a confirmar antes da fase 3B (seção 10.3) |
| Ponte interface-motor | Mensagens entre a página e o Web Worker | Mesmo contrato JSON da seção 9.2. FastAPI + Uvicorn só no modo de desenvolvimento |
| Interface | TypeScript + React + Vite | Estado com Zustand |
| Entrada de equações | MathLive (saída em LaTeX) | Separador decimal configurado para vírgula |
| Exibição de equações | KaTeX | Passos, fichas e exportação |
| Distribuição | Site estático com service worker (PWA), publicado no GitHub Pages pela integração contínua | Sem instalador e sem assinatura digital; domínio próprio opcional |
| Testes | pytest + Hypothesis (motor); Vitest + Playwright (interface) | Seção 5 |
| Animações | Manim Community (geração prévia) e Canvas (interativas) | Seção 9 |

As versões exatas são fixadas num arquivo de trava no início da fase 1, depois de confirmar na documentação atual de cada biblioteca as interfaces usadas (em especial o LaTeX emitido pelo MathLive e o backend IF97 do CoolProp). O analisador de LaTeX é próprio, sem biblioteca externa (decisão 0001 do repositório). O Amsior é distribuído sob a AGPL-3.0 (D-15). As bibliotecas incorporadas têm licença permissiva (MIT, BSD ou OFL nas fontes) e o Pyodide é MPL-2.0, todas compatíveis com a AGPL-3.0; a licença de cada biblioteca nova é conferida antes de entrar. Como a AGPL pede que o usuário de uma aplicação em rede tenha acesso ao código, a interface traz uma ligação para o repositório.

### Estrutura do repositório

```
amsior/
  motor/amsior/{expr,rules,steps,verify,units,numerics,props,interp,sheet,library,i18n,api}/
  motor/tests/{unit,corpus,propriedade}/
  interface/src/{blocos,editor,biblioteca,passos,estado}/   (inclui o trabalhador de cálculo e o service worker)
  biblioteca/{termodinamica,balancos,reatores,mecflu,calor,massa,opunit}/*.yaml
  biblioteca/_glossario.yaml  biblioteca/_hipoteses.yaml  biblioteca/_fontes.yaml
  propriedades/<fonte>/*.yaml
  animacoes/{cenas,saida}/
  docs/especificacao.md  docs/decisoes/
```

## 3. Modelo de dados

Há cinco estruturas persistentes, quatro descritas aqui e a tabela de propriedades dos livros na seção 7.5: a expressão (AmsiorExpr), o passo, a folha (`.amsior`) e a ficha (YAML). Todas têm esquema versionado e são validadas na leitura.

### 3.1 Expressão (AmsiorExpr)

A expressão é uma árvore JSON que preserva exatamente a forma escrita: `a - b` não vira `a + (-1)·b`, e a ordem dos termos é a do autor.

- **Nós**: `Num` (texto decimal exato ou racional), `Sym` (id do símbolo), `Add`, `Sub`, `Neg`, `Mul`, `Div`, `Pow`, `Sqrt`, `Root`, `Exp`, `Ln`, `Log` (com base), `Sin`, `Cos`, `Tan`, `Abs`, `Deriv`, `PDeriv` (com variáveis mantidas constantes), `Integral` (integrando, variável, limites opcionais), `Func` (função incógnita, como y(t)), `Eq` (lado esquerdo, lado direito) e as relações Ne, Gt, Ge, Lt e Le, usadas nas condições.
- **Símbolo**: `id`, `latex`, `grandeza` (id no glossário), `dimensao`, `papel` (variável, parâmetro, constante física, função) e `suposicoes` (real, positivo, não nulo, inteiro), além da lista depende\_de, com os símbolos de que ele é função (seção 4.3). As suposições vêm da grandeza: temperatura absoluta e pressão absoluta são positivas; isso decide, por exemplo, se o passo mostra ln x ou ln |x|.
- **Entrada única**: tudo entra como LaTeX restrito, convertido por um analisador descendente recursivo próprio (decisão 0001; gramática em docs/gramatica.md). O MathLive fornece esse LaTeX; as fichas usam a mesma sintaxe. Há um só analisador a testar.
- **Símbolos de várias letras** (Re, Nu, Pr, C\_p, ΔH\_vap): o analisador casa primeiro com os símbolos já conhecidos na folha ou na ficha; uma sequência desconhecida não é adivinhada, a interface pergunta se é um símbolo ou um produto.
- **Conversões**: AmsiorExpr → LaTeX (exibição, determinística), AmsiorExpr → SymPy (oráculo), SymPy → AmsiorExpr (apenas para resultados do oráculo, com normalização de apresentação). Nunca texto → SymPy.

### 3.2 Passo

Motor e demonstrações curadas produzem o mesmo registro, julgado pelo mesmo verificador. Além de regra, o passo traz operacao (nome, argumento, lado, símbolo, origem e, para derivar ou integrar, a declaração de identidade), que o verificador refaz pela sua própria tabela (decisões 0002 e 0003).

```json
{
  "indice": 3,
  "tipo": "algebra",
  "regra": "dividir_ambos_lados",
  "antes": {"Eq": ["...", "..."]},
  "depois": {"Eq": ["...", "..."]},
  "parametros": {"divisor": "..."},
  "justificativa": {"chave": "regra.dividir_ambos_lados", "args": {"divisor": "R T"}},
  "relacao": "equivalente",
  "condicoes": [{"expr": {"Ne": ["...", "0"]}, "origem": "hipotese", "satisfeita": null}],
  "certificado": {"metodo": "simbolico", "estado": "aprovado", "sob_hipotese": true,
                  "hipoteses": ["..."], "exigencias": ["..."], "amostragem": ["..."],
                  "versoes": {"sympy": "1.14.0", "mpmath": "1.3.0"}},
  "subpassos": []
}
```

| Campo | Valores |
| --- | --- |
| `tipo` | `algebra`, `calculo`, `substituicao`, `principio`, `aproximacao`, `numerico` |
| `relacao` | `equivalente` (⇔) ou `implica` (⇒, pode criar raízes estranhas), sempre lida sob as hipóteses do passo |
| `certificado.sob_hipotese` | calculado pelo verificador: a conta só fecha com alguma hipótese (condição declarada, igualdade substituída, variável tratada como constante numa integral, equação declarada identidade), listada em `hipoteses` |
| `certificado.metodo` | `simbolico`, `numerico`, `revisao_humana` |
| `certificado.estado` | `aprovado`, `reprovado`, `pendente` |

Os tipos `principio` (invocar a 1ª lei, um balanço) e `aproximacao` (desprezar um termo) só existem em demonstrações curadas e sempre exigem `revisao_humana`; vindos do motor, reprovam.

### 3.3 Folha (`.amsior`)

A folha é um documento JSON UTF-8 com `formato` (inteiro, começa em 1), `metadados`, `simbolos` e `blocos` em ordem de exibição. No navegador ela fica guardada no armazenamento local do dispositivo e pode ser baixada ou aberta como arquivo `.amsior` (seção 9.1).

| Bloco | Conteúdo |
| --- | --- |
| `texto` | Markdown restrito, sem HTML |
| `definicao` | Símbolo recebe valor com unidade ou expressão (`:=`) |
| `equacao` | Relação entre símbolos (`=`), ainda sem direção de cálculo |
| `resolucao` | Operação sobre uma equação (isolar, integrar, derivar, EDO), com passos e certificados em cache |
| `propriedade` | Propriedade de substância com origem escolhida (calculada ou pacote de livro), fonte e estado de referência |
| `interpolacao` | Tabela colada ou embutida, método e ponto |
| `tabela_variaveis` | Visão: símbolo, nome, valor, unidade, origem (dado, calculado, tabelado) |
| `grafico` | Expressão em função de uma variável, com parâmetros ajustáveis |
| `ficha` | Referência a uma ficha da biblioteca, com versão |

Regras de cálculo da folha:

1. **Atribuição única**: cada símbolo tem no máximo um bloco que o define. Uma segunda definição é erro, com sugestão de índice (T\_1, T\_2). Uma resolução do tipo isolar conta como a definição do símbolo-alvo.
2. **Ordem livre**: os blocos formam um grafo de dependências; o recálculo segue a ordem topológica, não a ordem na página.
3. **Ciclo**: dependência circular é informada como sistema acoplado, fora do escopo da v1.
4. **Recálculo incremental**: mudar um valor recalcula só os dependentes. Passos simbólicos não dependem de valores e não são refeitos.
5. **Cache**: cada `resolucao` guarda o hash da entrada e a versão do motor; versão diferente invalida o cache.
6. **Colisão de símbolos**: duas fichas que usam a mesma letra para grandezas diferentes (h de convecção e h de entalpia) disparam renomeação guiada ao entrar na mesma folha.

### 3.4 Ficha (YAML)

Uma ficha por arquivo, validada por esquema. Exemplo resumido:

```yaml
id: termo.clausius_clapeyron_integrada
versao: 1
estado: rascunho            # rascunho | auto_verificada | verificada
area: termodinamica
titulo: {pt: "Equação de Clausius-Clapeyron (forma integrada)"}
equacao: '\ln\frac{P_2}{P_1} = -\frac{\Delta H_{vap}}{R}\left(\frac{1}{T_2}-\frac{1}{T_1}\right)'
variaveis:
  - {simbolo: P_1, grandeza: pressao_saturacao, unidade_si: Pa, faixa: null}
  - {simbolo: T_1, grandeza: temperatura_absoluta, unidade_si: K}
  - {simbolo: "\\Delta H_{vap}", grandeza: entalpia_vaporizacao_molar, unidade_si: J/mol}
  - {simbolo: R, grandeza: constante_gases, constante: true}
hipoteses: [substancia_pura, equilibrio_liquido_vapor, vapor_gas_ideal,
            volume_liquido_desprezivel, dhvap_constante]
validade:
  texto: {pt: "Intervalos curtos de temperatura, longe do ponto crítico."}
  limites: []               # desigualdades verificáveis, quando houver
demonstracao:
  parte_de: [termo.clapeyron]
  passos:
    - {tipo: substituicao, usa: hipotese.volume_liquido_desprezivel, depois: '...'}
    - {tipo: substituicao, usa: termo.gas_ideal, depois: '...'}
    - {tipo: algebra, regra: separar_variaveis, depois: '...'}
    - {tipo: calculo, regra: integrar_ambos_lados, depois: '...'}
referencias:
  - fonte: svna               # definida em _fontes.yaml, com a última edição
    capitulo: null
    secao: null
    equacao: null
    pagina: null
    conferido: {por: null, em: null}
exemplo:
  dados: {P_1: "101325 Pa", T_1: "373,15 K", T_2: "393,15 K", "\\Delta H_{vap}": "40,66 kJ/mol"}
  origem_dos_dados: null     # origem declarada de cada propriedade (seção 7.5); os valores acima são ilustrativos
  pede: P_2
  esperado: null             # calculado e conferido na revisão
  tolerancia_rel: 1e-6
  comparacao_independente: {fonte: coolprop, grandeza: pressao_saturacao, desvio_aceito_rel: 0.05}
relacionadas: [termo.clapeyron, termo.antoine]
animacao: null
revisao: {automatica: null, humana: null, externo: null}
```

Campos obrigatórios para o estado `verificada`: todos os de `referencias` preenchidos e conferidos, `exemplo.esperado`, pelo menos uma hipótese do vocabulário controlado e todos os passos com certificado aprovado.

### 3.5 Ficha de conceito (D-13)

Explica um assunto em vez de uma equação: o que é, como funciona, quando se usa, com ilustrações e animações. Segue o mesmo fluxo de revisão das fichas de equação (seção 8.5), com redação própria (seção 8.6).

```yaml
id: reatores.cstr
tipo: conceito
versao: 1
estado: rascunho
area: reatores
titulo: {pt: "Reator contínuo de tanque agitado (CSTR)"}
resumo: {pt: "..."}
secoes:                       # texto em Markdown com LaTeX; cada seção pode ter figura
  - {titulo: {pt: "Como funciona"}, texto: {pt: "..."}, figura: reatores/cstr_esquema.svg}
  - {titulo: {pt: "Quando se usa"}, texto: {pt: "..."}}
  - {titulo: {pt: "Vantagens e limitações"}, texto: {pt: "..."}}
equacoes: [reatores.cstr_projeto, reatores.tempo_espacial]   # fichas de equação ligadas
exemplos:                     # contas verificadas pelo motor, como nas fichas de equação
  - {enunciado: {pt: "..."}, usa: reatores.cstr_projeto, pede: V}
animacao: {cena: reatores/cstr_mistura, interativa: reatores/levenspiel}
referencias: [{fonte: fogler, capitulo: null, secao: null, conferido: {por: null, em: null}}]
relacionadas: [reatores.pfr, reatores.cstr_em_serie]
revisao: {humana: null, externo: null}
```

Afirmações quantitativas do texto entram como `exemplos`, para que o motor as confira; o restante passa pela revisão humana (V7).

## 4. Motor de passos

O motor aplica regras nomeadas sobre a AmsiorExpr, uma por vez, e só entrega a sequência se todos os passos receberem certificado. Ele não é um CAS geral: cobre bem os padrões da engenharia química e recusa com clareza o que não cobre.

### 4.1 Regra

Cada regra do catálogo declara:

- `id` e `tipo` (álgebra, cálculo);
- **aplicabilidade**: padrão estrutural que a expressão precisa ter;
- **transformação**: função pura AmsiorExpr → AmsiorExpr, que mexe só no que a regra descreve;
- **relação** (equivalente, implica) e **condições** geradas (divisor não nulo, argumento de logaritmo positivo);
- **operação declarada**, em forma que o verificador consegue refazer sozinho (seção 5.1);
- **justificativa**: chave no catálogo de textos, em versão curta (“Dividindo ambos os lados por R·T”) e longa (com o motivo: “para desfazer a multiplicação que acompanha P”);
- `fundivel`: se o passo pode ser fundido ao vizinho no modo resumido.

Uma condição é confrontada com as suposições dos símbolos. Se já está garantida (T > 0), fica registrada sem poluir a tela; se não está, aparece ao aluno como “supondo que…”.

### 4.2 Isolar variável

1. **Pré-checagem**: a equação é dimensionalmente homogênea e contém o alvo.
2. **Contagem** de ocorrências do alvo.
3. **Uma ocorrência — descascar**: percorre-se o caminho da raiz até o alvo, desfazendo a operação mais externa a cada passo, conforme a tabela abaixo (n inteiro positivo).
4. **Várias ocorrências — reunir**, tentando nesta ordem: combinar logaritmos ou potências que fundem ocorrências; eliminar denominadores que contêm o alvo; expandir e agrupar; se linear no alvo, fatorar e dividir; se quadrática, fórmula resolutiva com análise do discriminante; se a mesma função do alvo se repete (e^x, x^n, ln x), substituição u.
5. **Acabamento**: simplificações de apresentação (cancelar fatores, fração de frações, sinais), cada uma como passo. Nada é expandido sem necessidade.
6. **Raízes**: se algum passo teve relação `implica`, cada candidata é testada na equação original; raízes múltiplas são filtradas pelas suposições (pressão positiva descarta a raiz negativa) e o descarte é explicado.
7. **Recusa**: sem forma fechada elementar, o motor diz isso. Se o oráculo encontrar solução, ela aparece rotulada “resultado sem passos”, ainda sujeita à verificação de ponta a ponta. Limite: 40 passos.

| Forma (u contém o alvo) | Passo | Relação e condição |
| --- | --- | --- |
| u + A = B | Subtrair A dos dois lados | Equivalente |
| A − u = B | Somar u e subtrair B dos dois lados | Equivalente |
| A·u = B | Dividir por A | Equivalente se A ≠ 0 |
| u / A = B | Multiplicar por A | Equivalente (A ≠ 0 já é domínio) |
| A / u = B | Multiplicar por u, dividir por B | Equivalente se B ≠ 0 |
| u^n = B, n ímpar | Raiz n-ésima | Equivalente |
| u^n = B, n par | u = ±B^(1/n) | Exige B ≥ 0; só o ramo positivo se u > 0 |
| u^a = B, a não inteiro | Elevar a 1/a | Exige u > 0 e B > 0 |
| √u = B | Elevar ao quadrado | Implica; exige B ≥ 0 |
| e^u = B | Logaritmo natural | Exige B > 0 |
| A^u = B | u = ln B / ln A | Exige A > 0, A ≠ 1, B > 0 |
| ln u = B | Exponencial | Equivalente |
| log\_b u = B | u = b^B | Equivalente |
| \|u\| = B | u = ±B | Exige B ≥ 0 |
| sen u = B (e análogas) | Função inversa, ramo principal | Sob hipótese; aviso de periodicidade |

### 4.3 Integrais

Antes de integrar, o motor checa **dependências**: cada símbolo da folha declara de quem depende. Um símbolo só sai da integral como constante se for independente da variável de integração. Se C\_p aparece em ∫C\_p dT sem dependência declarada, o Amsior pergunta: constante (hipótese registrada no passo) ou função de T (pede a expressão). O mesmo vale para ∫V dP e ∫P dV, que exigem a relação entre as variáveis (equação de estado, caminho do processo).

Regras da v1: linearidade (constante e soma); potência com n ≠ −1; 1/x; exponencial; substituição linear u = ax + b; substituição quando a derivada de u está presente; frações parciais com fatores lineares distintos; por partes em uma aplicação; teorema fundamental com avaliação nos limites.

Regra obrigatória de acabamento: diferenças de logaritmos são combinadas em logaritmo de razão. O resultado mostrado é ln(T\_2/T\_1), nunca ln T\_2 − ln T\_1, porque o argumento de um logaritmo precisa ser adimensional.

Padrões reconhecidos e nomeados na explicação:

| Padrão | Forma |
| --- | --- |
| Calor sensível com C\_p polinomial | ∫(a + bT + cT² + dT⁻²) dT |
| Variação de entropia a P constante | ∫(C\_p / T) dT |
| Termo de pressão de gás ideal | ∫ dP / P |
| Trabalho isotérmico de gás ideal | ∫P dV com P = nRT/V |
| Processo politrópico | ∫P dV com PV^n constante, n ≠ 1 |
| Trabalho de eixo | ∫V dP com V(P) explícito |

A sequência de regras pode ser proposta pelo integrador manual do SymPy, se sua interface estiver estável na versão fixada; a exibição e o certificado são sempre do Amsior.

### 4.4 Derivadas

Regras: constante, soma, produto, quociente, cadeia, potência, exponencial, logaritmo, trigonométricas. Derivadas parciais usam a notação (∂/∂T)\_P e a mesma checagem de dependências: derivar “mantendo P constante” só é aceito se os demais símbolos forem independentes ou tiverem dependência explícita. Diferencial total entra na v1; derivação implícita fica para a v1.1.

### 4.5 EDOs de 1ª ordem

1. **Classificar** e mostrar a forma canônica: separável, dy/dx = f(x)·g(y), ou linear, dy/dx + p(x)·y = q(x).
2. **Separável**: separar as variáveis (condição g(y) ≠ 0; as soluções constantes com g(y) = 0 são informadas à parte), integrar os dois lados, introduzir a constante.
3. **Linear**: calcular o fator integrante exp(∫p dx), multiplicar, reconhecer a derivada do produto, integrar.
4. **Condição inicial**: substituir e isolar a constante.
5. **Explicitar** y, quando possível.

Integrar e isolar são chamadas aos motores 4.2 e 4.3; seus passos aparecem como `subpassos` do passo que os invocou, recolhíveis na interface. Casos de teste obrigatórios: reator batelada de 1ª ordem, capacitância global (resfriamento de Newton), tanque de mistura com entrada constante.

### 4.6 Níveis de detalhe

A mesma lista de passos é exibida em dois níveis: **completo** (todos) e **resumido** (passos `fundivel` unidos ao vizinho, com a justificativa composta). O certificado do passo fundido é a conjunção dos certificados originais.

### 4.7 Tipo da equação (D-12)

Antes de resolver, o motor classifica a equação na variável escolhida, pela classificação usual do ensino:

| Tipo | Quando | Exemplo |
| --- | --- | --- |
| 1º, 2º, 3º grau ou polinomial de grau n | expressão racional inteira na variável | `PV = nRT` em V; Bernoulli em v₁ (2º grau) |
| Racional fracionária | a variável aparece no denominador; o grau é o de depois de tirar os denominadores | Charles em T₁ |
| Irracional | a variável aparece sob raiz ou com expoente fracionário | Dittus-Boelter em Re |
| Exponencial, logarítmica, trigonométrica, modular | a variável aparece só dentro dessa função | Arrhenius em Eₐ; Clausius-Clapeyron em P₂ |
| Mista | a variável aparece fora e dentro de uma função transcendente | LMTD em ΔT₂ (sem forma fechada) |

A etiqueta aparece no bloco de equação e no cabeçalho da resolução e leva à ficha de Matemática do tipo. Ela é só informativa: não muda passos nem verificação.

## 5. Verificação e conformidade científica

A conformidade é garantida por sete camadas independentes; um passo só aparece como verificado se passar pelas que se aplicam a ele, e o que a máquina não consegue julgar fica explicitamente a cargo da revisão humana. O verificador não confia no motor: ele recebe “antes”, “depois” e a operação declarada, e refaz a conta por outro caminho.

| Camada | O que confere | Como | Aplica-se a |
| --- | --- | --- | --- |
| V1 Certificado do passo | A operação declarada leva exatamente de “antes” a “depois” | Refaz a operação no SymPy e testa identidade dos dois lados | Todo passo de álgebra e cálculo |
| V2 Ponta a ponta | A resposta satisfaz o problema original | Substitui a solução na equação inicial; resíduo nulo, ramo a ramo | Isolar, EDO |
| V3 Oráculo independente | O resultado coincide com o de outro algoritmo | `solve`, `integrate`, `dsolve` e `checkodesol` do SymPy | Isolar, integrais, derivadas, EDO |
| V4 Cálculo | A primitiva e a integral definida estão certas | Deriva a primitiva e compara com o integrando; quadratura numérica de alta precisão em pontos sorteados | Integrais |
| V5 Dimensional | Cada passo é homogêneo; argumentos de ln, exp e trigonométricas são adimensionais | Análise dimensional simbólica com as grandezas dos símbolos | Todo passo |
| V6 Exemplo numérico | A ficha reproduz o valor esperado e bate com fonte independente | Cálculo com unidades; comparação dentro da tolerância declarada | Fichas |
| V7 Revisão humana | Hipóteses físicas, fidelidade à fonte, citação, clareza | Lista de conferência assinada (seção 8.5) | Fichas; passos `principio` e `aproximacao` |

### 5.1 Teste de identidade (V1)

O verificador trabalha na árvore do Amsior; o SymPy só entra na via simbólica (decisão 0003). Para certificar que duas expressões A e B são idênticas, duas vias independentes rodam sempre:

1. **Simbólica**: `simplify(A − B) == 0` sob as suposições dos símbolos, com variantes (`expand`, `cancel`, `logcombine`, `powsimp`). Uma diferença que simplifica a constante não nula reprova.
2. **Numérica**: avaliador próprio da árvore em mpmath, que não passa pelo SymPy. Sorteia 20 pontos dentro das suposições e condições, com magnitudes de 10⁻⁹ a 10⁹ em seis estratos e pontos perto dos números da expressão; avalia cada lado a 60 e 120 dígitos (240 se instável) e exige `|A − B| ≤ 10⁻³⁰·max(|A|, |B|)` mais o ruído medido. Subexpressões que escolhem ramo (argumento de módulo, `w` em `√(w²)`) precisam ser vistas com os dois sinais. Funções declaradas (`C_A(t)`) viram funções suaves sorteadas; derivadas e integrais definidas são calculadas numericamente.
3. Simbólica prova e numérica confere: certificado `simbolico`. Simbólica prova e numérica diverge: reprovado (erro de conversão). Simbólica inconclusiva e numérica confere: certificado `numerico`, com selo próprio. Qualquer outro caso equivale a reprovado.

A semente do sorteio é fixa por passo, para que o resultado seja reprodutível.

Derivadas parciais com variáveis mantidas, derivadas de variáveis sem dependência declarada e integrais indefinidas viram objetos opacos, iguais dos dois lados: carregá-los é verificável, “calculá-los” reprova.

**Domínio.** Cada nó que só existe em parte dos reais gera uma obrigação (denominador ≠ 0, argumento de ln > 0, radicando de raiz par ≥ 0, base de potência não inteira > 0, integrando definido no intervalo). Obrigação nova em “depois” exige condição declarada; obrigação de “antes” que some em “depois” limita a relação a `implica`; obrigação falsa com certeza reprova. V2 confere as obrigações da equação original na solução.

Operações dos dois lados (somar, multiplicar, aplicar função) são certificadas lado a lado: o verificador aplica a operação declarada a cada lado de “antes” e exige identidade com o lado correspondente de “depois”. Reescritas de um lado só (fatorar, combinar logaritmos) exigem identidade direta. Substituições exigem identidade após aplicar a definição ou a ficha citada em `usa`.

O verificador mantém sua própria tabela de quais operações preservam a equivalência e sob que condições. Um passo cuja relação ou cujas condições declaradas sejam mais otimistas que essa tabela é reprovado, mesmo que a conta esteja certa: dividir por uma expressão que pode ser nula sem declarar a condição, ou elevar ao quadrado declarando equivalência, não passa.

### 5.2 Política de falha

- Passo reprovado **nunca é exibido**. A resolução inteira é descartada e o Amsior mostra apenas o resultado do oráculo, rotulado “sem passos”, se este passar em V2.
- Se nem o resultado passar em V2, nada é mostrado além da mensagem de que não foi possível resolver com garantia.
- Toda reprovação é gravada num registro local (entrada, regra, resíduo) para virar caso de teste.

### 5.3 Selos visíveis ao usuário

| Selo | Significado |
| --- | --- |
| Verificado | Certificado simbólico em V1 e aprovação em V5 |
| Verificado numericamente | V1 por amostragem de alta precisão; V5 aprovada |
| Sob hipótese | Passo válido só sob hipótese não garantida pelas suposições (condição, igualdade substituída, variável constante numa integral), que é mostrada; calculado pelo verificador |
| Revisado | Passo de princípio ou aproximação, aprovado em V7 |

### 5.4 Suíte de testes

- **Unitários por regra**: cada regra tem casos que deve aceitar, casos que deve recusar e casos em que a condição precisa aparecer.
- **Corpus da biblioteca**: para toda ficha, isolar cada variável. O resultado esperado é “isola com passos” ou “declarada não isolável” (lista explícita); qualquer outro desfecho quebra a integração contínua.
- **Testes de propriedade** (Hypothesis): equações geradas a partir de modelos (linear, racional, potência, exponencial, logarítmica, compostas até profundidade 4); para cada uma, V2 precisa passar.
- **Verificador sob ataque**: passos propositalmente errados (sinal trocado, divisão esquecida de um lado, raiz perdida, logaritmo de soma) precisam ser todos reprovados. Esta suíte mede o verificador, não o motor.
- **Regressão**: todo erro encontrado em uso vira teste antes da correção.

### 5.5 Limites do que é garantido

A máquina garante a matemática e as dimensões. Ela não garante que a hipótese física se aplica ao problema do aluno, nem que uma correlação empírica está sendo usada dentro da faixa. Por isso toda ficha exibe hipóteses e validade junto da equação, e a folha avisa quando um valor sai da faixa declarada (seção 7.3).

## 6. Unidades, números e constantes

Todo valor entra com unidade, é convertido para o SI na entrada, calculado em SI e convertido de volta só na exibição. Não existe número sem unidade, exceto os adimensionais declarados.

### 6.1 Grandezas e dimensões

O glossário (`_glossario.yaml`) define cada grandeza com dimensão, unidade SI, unidades de exibição aceitas e suposições. A dimensão do símbolo vem da grandeza, não do valor digitado, o que permite a análise dimensional simbólica antes de existir qualquer número.

| Armadilha | Regra do Amsior |
| --- | --- |
| Temperatura absoluta e diferença de temperatura | Grandezas distintas. Absoluta: °C é convertido para K com deslocamento. Diferença: 1 °C = 1 K, sem deslocamento. Nenhuma conta é feita em °C: a conversão para K ocorre na entrada |
| Pressão absoluta e manométrica | Equações usam sempre a absoluta. Entrada manométrica é aceita com a pressão atmosférica explícita na folha |
| Base molar e base mássica | Grandezas distintas (J/mol e J/kg). A conversão exige a massa molar como símbolo visível |
| mol e kmol | Convertidos como qualquer prefixo; R acompanha a unidade |
| Argumento de ln, exp, seno | Precisa ser adimensional; caso contrário, erro de V5 |
| Frações e porcentagens | Adimensionais; entrada em % é convertida para fração |
| Soma de grandezas diferentes com a mesma dimensão (calor e trabalho) | Permitida; a distinção é do glossário, não da análise dimensional |

### 6.2 Equações empíricas dimensionais

Correlações como a de Antoine não são dimensionalmente homogêneas: os coeficientes valem para unidades fixas. A ficha marca `empirica_dimensional: true` e fixa a unidade de cada variável. O Amsior converte os valores para essas unidades, calcula com números puros e reconverte. Cada conjunto de coeficientes carrega as unidades, a faixa de validade e a fonte, e não pode ser usado sem as três.

### 6.3 Números

- **Cálculo**: ponto flutuante de dupla precisão, sem arredondamento intermediário. A verificação usa mpmath (seção 5.1).
- **Exibição**: 4 algarismos significativos por padrão, configurável de 3 a 8 por folha. Notação científica acima de 10⁶ e abaixo de 10⁻³.
- **Formato pt-BR**: vírgula decimal; ponto e vírgula separa argumentos e itens de lista; separador de milhar não é aceito na entrada e aparece como espaço fino na saída. O arquivo `.amsior` guarda números sempre com ponto, independentemente do idioma.
- **Exatos**: números digitados nas equações (o 2 de x², o 1/2) são racionais exatos na árvore; só viram decimais na avaliação.

### 6.4 Constantes físicas

As constantes ficam num único arquivo, com valor, unidade e fonte, e um teste as confronta com `scipy.constants`.

| Constante | Valor | Natureza |
| --- | --- | --- |
| R, constante dos gases | 8,314462618… J/(mol·K) | Exata desde o SI de 2019 (N\_A · k) |
| N\_A, Avogadro | 6,02214076 × 10²³ mol⁻¹ | Exata |
| k, Boltzmann | 1,380649 × 10⁻²³ J/K | Exata |
| σ, Stefan-Boltzmann | 5,670374419… × 10⁻⁸ W/(m²·K⁴) | Derivada de constantes exatas |
| g, gravidade padrão | 9,80665 m/s² | Convencional |
| atm, atmosfera padrão | 101 325 Pa | Convencional |

Valores de R em outras unidades (0,08206 L·atm/(mol·K) e similares) nunca são digitados: saem da conversão de unidades.

## 7. Propriedades termodinâmicas e interpolação

O Amsior tem duas origens de propriedades, e o usuário escolhe qual usar: as formulações de referência calculadas (7.1 e 7.2) e a biblioteca de propriedades dos livros (7.5). Todo valor exibido informa a origem, a fonte, o estado de referência e a faixa de validade.

### 7.1 Fluidos puros

- **Fonte**: CoolProp, equações de estado multiparamétricas. Água pela IAPWS-95; a IAPWS-IF97 fica disponível como opção, para quem quer reproduzir tabelas industriais.
- **Estado de referência**: entalpia e entropia dependem de um zero arbitrário, que varia entre livros e entre fluidos. O bloco `propriedade` mostra a convenção em uso e avisa que valores absolutos de h e s podem diferir dos de uma tabela impressa por uma constante; diferenças (Δh, Δs) não são afetadas.
- **Especificação do estado**: dois valores independentes. Na saturação, T e P não são independentes: o Amsior exige o título x ou outra propriedade, e explica o motivo.
- **Fase**: o resultado informa a fase (líquido comprimido, mistura saturada, vapor superaquecido, supercrítico).
- **Desempenho**: cache por (fluido, par de entrada, valores arredondados a 12 dígitos); chamadas em lote para gráficos.
- **Validação**: testes automatizados comparam o CoolProp com os valores de verificação publicados nos documentos da IAPWS, transcritos da fonte oficial e conferidos na fase 3.

### 7.2 Correlações (C\_p de gás ideal, pressão de vapor)

Coeficientes vêm das bases das bibliotecas chemicals/thermo, que registram a origem de cada conjunto. Cada correlação entra no Amsior com forma funcional, unidades, T mínima e T máxima, e identificação da fonte. Coeficientes e valores tabelados de um livro específico ficam na biblioteca de propriedades dos livros (7.5).

### 7.3 Faixa de validade

Valor fora da faixa de uma correlação, de uma ficha ou de uma equação de estado gera aviso visível no bloco e na tabela de variáveis. O Amsior não extrapola em silêncio; o usuário pode prosseguir, e o resultado fica marcado como fora da faixa.

### 7.4 Interpolação

| Método | Passo a passo | Uso |
| --- | --- | --- |
| Linear | Sim: fórmula, substituição dos números, resultado | Padrão para tabelas |
| Bilinear (duas entradas, ex.: T e P) | Sim: duas interpolações numa variável, depois uma na outra | Tabelas de vapor superaquecido |
| Linear em escala transformada (ln P contra 1/T) | Sim | Pressão de vapor |
| Spline cúbica monotônica (PCHIP) | Não: informa o método e o valor | Curvas suaves sem oscilação entre pontos |
| Spline cúbica natural | Não | Opcional, com aviso de possível oscilação |

Fórmula exibida na interpolação linear:

```latex
y = y_1 + \frac{(x - x_1)\,(y_2 - y_1)}{x_2 - x_1}
```

Regras:

1. **Entrada**: o usuário cola o trecho da tabela (tabulação ou ponto e vírgula, vírgula decimal) ou escolhe um fluido embutido. O Amsior localiza sozinho os pontos vizinhos.
2. **Extrapolação**: bloqueada por padrão; liberada com aviso.
3. **Mudança de fase**: interpolar entre pontos de fases diferentes é recusado, com explicação.
4. **Comparação didática**: para fluidos embutidos, o bloco mostra o valor interpolado, o valor calculado diretamente pela equação de estado e o desvio entre eles.
5. **Unidades**: cada coluna tem unidade; o resultado segue as regras da seção 6.

### 7.5 Biblioteca de propriedades dos livros (D-10)

É uma biblioteca à parte da de equações: guarda os dados dos apêndices e tabelas das fontes, organizados em pacotes por livro, e cada pacote pode ser ligado ou desligado. Ela convive com a origem calculada; nenhuma substitui a outra.

| Tipo de dado | Exemplos |
| --- | --- |
| Constantes de substância pura | Massa molar, temperatura e pressão críticas, fator acêntrico, ponto normal de ebulição |
| Coeficientes de correlações | C\_p de gás ideal, pressão de vapor (Antoine), viscosidade em função de T |
| Propriedades de reação | Entalpia e energia de Gibbs de formação, calor de combustão |
| Propriedades termofísicas tabeladas | Massa específica, calor específico, condutividade, viscosidade e número de Prandtl de sólidos, líquidos e gases em função de T |
| Tabelas de saturação e de vapor | Água e refrigerantes |
| Propriedades de transporte e de superfície | Difusividades, emissividades |

**Estrutura.** Um arquivo por tabela, em `propriedades/<fonte>/<tabela>.yaml`, com: fonte e edição; identificação da tabela no livro (número, título, página); grandeza e unidade de cada coluna; estado de referência; faixa de validade; forma funcional, quando são coeficientes; notas de rodapé que mudam a leitura dos dados; registros por substância, identificada por nome e número CAS; campo `conferido`.

**Transcrição.** Vale a regra das citações (seção 8.4): nenhum valor é escrito de memória, por pessoa ou por modelo. Ruan transcreve da última edição ou importa por planilha-modelo (CSV), e cada tabela passa por três conferências antes de ficar disponível:

1. Releitura por amostragem contra o livro, com nome e data em `conferido`.
2. Checagens automáticas: unidades válidas, valores dentro de limites físicos, tendência coerente com a temperatura, substância reconhecida pelo CAS.
3. Comparação com a origem calculada: desvio acima do limite da grandeza é sinalizado para reconferir a digitação. A máquina sinaliza, não corrige; o valor do livro prevalece no pacote do livro.

**Uso opcional, em três níveis.**

| Nível | O que se escolhe | Padrão |
| --- | --- | --- |
| Aplicativo | Quais pacotes de livro estão ligados | Todos desligados; só a origem calculada |
| Folha | Ordem de preferência entre as origens (por exemplo, livro-base da área e, na falta, calculada) | Calculada |
| Bloco `propriedade` | Origem daquele valor, explicitamente | Herda a da folha |

**Exibição.** Todo valor vindo de livro traz rótulo com livro, edição e tabela. O bloco oferece a comparação entre o valor do livro e o calculado, com o desvio. Se o ponto pedido cai entre linhas da tabela, a interpolação segue a seção 7.4, com passos.

**Sem mistura silenciosa.** Entalpias e entropias de origens com estados de referência diferentes não podem ser combinadas numa mesma conta sem aviso. A folha detecta o caso e explica o motivo.

**Direitos autorais.** Valores numéricos isolados são fatos, mas a seleção e a organização de uma tabela podem ser protegidas, e reproduzir apêndices extensos num aplicativo distribuído pode exigir autorização da editora. Por isso os pacotes são arquivos separados do instalador: Ruan pode usá-los desde já no próprio computador, e a distribuição a alunos depende de resolver o ponto jurídico registrado na seção 10.3 (autorização da editora, importação feita pela instituição que possui os livros, ou restrição a dados de fontes abertas).

**Implementação.** O módulo `props` ganha o subpacote `props.livros` (carga, validação, busca e interpolação em tabelas). A rota `/propriedade` recebe o campo `origem`, e `GET /propriedades/pacotes` lista os pacotes e seu estado.

## 8. Biblioteca de equações

A biblioteca é um conjunto de arquivos YAML versionados em Git; uma ficha só chega ao aluno com selo depois de passar pela verificação automática e pela conferência de Ruan contra o livro.

### 8.1 Áreas e livro-base

Cada área segue a notação de um livro-base (D-06), sempre na última edição (D-09). As edições abaixo foram consultadas em 13/11/2026 e ficam registradas em `_fontes.yaml` com ano e ISBN; números de equação e de página valem só para a edição registrada.

| Área | Livro-base | Última edição |
| --- | --- | --- |
| Termodinâmica | [Smith, Van Ness, Abbott e Swihart](https://www.mheducation.com/highered/product/Introduction-to-Chemical-Engineering-Thermodynamics-Smith.html) | 9ª, 2022 |
| Balanços de massa e energia | [Felder, Rousseau e Bullard](https://www.wileyplus.com/felder-elementary-principles-of-chemical-processes-4e/) | 4ª, 2016; a [5ª está anunciada](https://www.schweitzer-online.de/en/buch/Felder/Elementary-Principles-Chemical-Processes/9781394462179/A77004195/) para 2028 |
| Reatores | [Fogler, Goldsmith, Nikolla e Singh](https://pearson.com/en-us/subject-catalog/p/elements-of-chemical-reaction-engineering/P200000012605/9780135337646) | 7ª, 2025 |
| Mecânica dos fluidos | [Fox, McDonald e Mitchell](https://www.wiley-vch.de/de/fachgebiete/ingenieurwesen/fox-and-mcdonald-39-s-introduction-to-fluid-mechanics-emea-edition-978-1-119-66595-3) | 10ª, 2020 |
| Transferência de calor | [Incropera (Bergman, Lavine, Incropera e DeWitt)](https://www.wileyplus.com/incropera-fundamentals-heat-mass-transfer-8e/) | 8ª, 2017 |
| Transferência de massa | [Bird, Stewart e Lightfoot](https://gov.wiley.com/WileyCDA/WileyTitle/productCd-0470115394.html) | 2ª revisada, 2007 |
| Operações unitárias | [McCabe, Smith e Harriott](https://Www.Wikipedia.org/wiki/Unit_Operations_of_Chemical_Engineering) | 7ª, 2004 |
| Matemática (D-13) | A definir (seção 10.3) | — |

Fontes de apoio, também na última edição:

| Fonte | Última edição |
| --- | --- |
| [Sandler](https://www.wiley-vch.de/en/areas-interest/engineering/chemical-biochemical-and-engineering-thermodynamics-978-0-470-50479-6), termodinâmica | 5ª, 2017 |
| [Elliott, Diky, Knotts e Wilding](https://www.mheducation.com/highered/mhp/product/properties-gases-liquids-sixth-edition.html), The Properties of Gases and Liquids (sucede Poling, Prausnitz e O'Connell) | 6ª, 2023 |
| [Himmelblau e Riggs](https://www.oreilly.com/library/view/-/9780137327164/), balanços | 9ª, 2022 |
| [Perry (Green e Southard)](https://wikipedia.com/wiki/Perry%27s_Handbook), manual | 9ª, 2018 |
| Levenspiel, reatores; Treybal, transferência de massa | A confirmar (seção 10.3) |

A tabela traz as edições originais, em inglês. Quando a tradução brasileira mais recente for de edição anterior, numeração e páginas diferem; a escolha entre citar o original ou a tradução está na seção 10.3. Fogler mudou de autoria na 7ª edição, e a conferência das fichas de reatores deve ser feita nela.

### 8.2 Glossário e divergências de notação

O glossário identifica a **grandeza**, não a letra. A ficha diz qual letra usa para cada grandeza, seguindo o livro-base. Assim a mesma letra pode significar coisas diferentes em áreas diferentes sem ambiguidade interna.

| Letra | Colisão conhecida | Tratamento |
| --- | --- | --- |
| h | Coeficiente de convecção (calor) e entalpia específica (termodinâmica) | Renomeação guiada quando as duas entram na mesma folha |
| U | Energia interna e coeficiente global de transferência de calor | Idem |
| k | Condutividade térmica e constante de velocidade de reação | Idem |
| q, Q | Taxa de calor, fluxo de calor, calor trocado, vazão volumétrica | A ficha explicita a grandeza e a unidade ao lado da equação |
| W | Trabalho feito sobre o sistema ou pelo sistema | Convenção IUPAC em todo o Amsior; ver abaixo |

**Sinal do trabalho**: o Amsior adota ΔU = Q + W, com W positivo quando feito sobre o sistema. Quando o livro-base de uma área usa a convenção oposta (caso do balanço de energia de reatores em Fogler), a ficha apresenta a equação na convenção IUPAC e traz uma nota fixa mostrando a forma do livro e a troca de sinal. A nota faz parte da revisão humana.

### 8.3 Hipóteses

As hipóteses vêm de um vocabulário controlado (`_hipoteses.yaml`): cada uma tem id, enunciado, e, quando possível, a consequência matemática que o verificador pode aplicar (gás ideal: PV = nRT; regime permanente: derivadas no tempo nulas). Uma ficha não pode citar hipótese fora do vocabulário; criar uma nova é uma alteração revisada. Isso permite buscar “todas as fichas que supõem gás ideal” e impede enunciados divergentes da mesma hipótese.

### 8.4 Citações (D-05)

1. A ficha nasce com fonte, capítulo e seção propostos, marcados como não conferidos.
2. Ruan localiza a equação na última edição da fonte e preenche número da equação e página, corrigindo capítulo e seção se preciso.
3. O campo `conferido` recebe nome e data. Sem ele, a citação aparece ao aluno apenas como “ver livro-base, capítulo indicado”, sem número.
4. Nenhum número de equação ou de página é escrito de memória, por pessoa ou por modelo.

Quando sai edição nova de uma fonte, as fichas e as tabelas de propriedades que a citam perdem o campo `conferido` e voltam a aparecer sem número de equação até a reconferência; o conteúdo matemático já verificado não muda de estado. A existência de edições novas é checada no início de cada fase do roteiro.

### 8.5 Fluxo de revisão (D-08)

| Estado | Como se chega | Visível ao aluno |
| --- | --- | --- |
| `rascunho` | Ficha criada | Não |
| `auto_verificada` | Integração contínua aprova V1 a V6 em tudo o que é verificável por máquina | Sim, com aviso “em revisão” |
| `verificada` | Ruan assina a lista de conferência | Sim, com selo |

Qualquer alteração de conteúdo numa ficha verificada a devolve para `rascunho` e incrementa a versão.

Na etapa automática, V6 confere que o exemplo calcula, que as unidades fecham e que o resultado fica dentro do desvio aceito em relação à fonte independente. O valor esperado é congelado na revisão humana e passa a servir de teste de regressão. Passos de princípio e de aproximação ficam pendentes até essa revisão. Lista de conferência da revisão humana:

- [ ] A equação coincide com a da fonte, consideradas a notação e a convenção de sinais.
- [ ] As hipóteses listadas são as que a fonte usa, sem faltar nem sobrar.
- [ ] A faixa de validade corresponde à da fonte.
- [ ] Cada passo de princípio ou aproximação da demonstração está fisicamente justificado.
- [ ] O texto é próprio, sem trechos copiados.
- [ ] Capítulo, seção, número da equação e página conferidos na última edição da fonte.
- [ ] O exemplo foi refeito à mão ou comparado com exemplo resolvido da fonte.
- [ ] Unidades e faixas típicas das variáveis fazem sentido.

O campo `revisao.externo` aceita o nome de um professor revisor, sem ser exigido.

### 8.6 Redação e direitos autorais

Equações, leis físicas e dados são usados livremente; o texto das demonstrações e dos exemplos é sempre próprio, com dados de exemplo próprios, citando a fonte. Figuras de livros não são reproduzidas; tabelas de propriedades seguem a seção 7.5. Padrão de redação: frases curtas, voz de professor no quadro, um motivo por passo.

### 8.7 Lista candidata de fichas

São 56 candidatas; a lista final (cerca de 50) fecha no início da fase 2. As cinco primeiras, em negrito, servem de modelo.

| Área | Fichas |
| --- | --- |
| Termodinâmica (14) | **Gás ideal**; **1ª lei para sistema fechado**; definição de entalpia; **calor sensível com C\_p(T)**; C\_p − C\_v = R; adiabático reversível de gás ideal; trabalho isotérmico reversível; variação de entropia de gás ideal; fator de compressibilidade; van der Waals; Clapeyron; **Clausius-Clapeyron**; **Antoine**; lei de Raoult |
| Balanços (6) | Balanço geral de massa; balanço por componente com extensão de reação; conversão e excesso; balanço de energia em sistema aberto em regime permanente; calor de reação pela lei de Hess; calor de reação em função da temperatura |
| Reatores (8) | Definição de conversão; equação de projeto do batelada; do CSTR; do PFR; Arrhenius; lei de velocidade de potência; tempo espacial; 1ª ordem integrada em batelada |
| Mecânica dos fluidos (7) | Lei de Newton da viscosidade; número de Reynolds; continuidade; Bernoulli; balanço de energia mecânica com perdas; Darcy-Weisbach; Hagen-Poiseuille |
| Transferência de calor (15) | Lei de Fourier; parede plana e resistência térmica; parede composta; condução radial em cilindro; raio crítico de isolamento; lei de resfriamento de Newton; capacitância global e número de Biot; aleta de ponta adiabática; eficiência de aleta; Dittus-Boelter; Stefan-Boltzmann; reciprocidade do fator de forma; coeficiente global U; LMTD; efetividade-NTU |
| Transferência de massa (1) | 1ª lei de Fick |
| Operações unitárias (5) | Volatilidade relativa; linha de operação de McCabe-Thiele; Fenske; Kremser; Rachford-Rice (implícita, sem isolamento na v1) |

Fichas de conceito candidatas (D-13), a confirmar com a lista final. Em negrito, as duas fichas-modelo.

| Seção | Fichas de conceito |
| --- | --- |
| Matemática (12) | Expressões algébricas e sua classificação (racionais inteiras, fracionárias, irracionais; monômios, polinômios e grau); equação do 1º grau; equação do 2º grau (discriminante, dois ramos); polinomiais de grau maior; **equação racional** (domínio, eliminar denominadores, raízes estranhas); equação irracional (elevar ao quadrado cria raízes estranhas); exponenciais e logaritmos (propriedades, mudança de base, por que o argumento precisa ser adimensional); equação exponencial e logarítmica; módulo e trigonométricas com ramo principal; equações mistas e por que não têm forma fechada; domínio, equivalência e implicação (o que significa "sob hipótese"); grandezas, dimensões e homogeneidade |
| Reatores (9) | Batelada; semibatelada; **CSTR**; PFR; leito fixo (PBR); CSTRs em série e a aproximação do PFR; reator com reciclo; isotérmico, adiabático e com troca térmica; o gráfico de Levenspiel e a escolha entre CSTR e PFR |

Cada ficha de Reatores traz o esquema do equipamento, como funciona, onde se usa na indústria, vantagens e limitações, a equação de projeto ligada e uma animação (seção 9.3).

## 9. Interface, API e animações

A interface tem três regiões fixas: a folha no centro, a tabela de variáveis à direita e a biblioteca à esquerda. Tudo o que ela mostra de matemática vem do motor pela API.

### 9.1 Interface

- **Folha**: blocos empilhados, editáveis no lugar; inserir bloco por menu ou atalho; arrastar para reordenar.
- **Bloco de equação**: campo MathLive. Clicar numa variável da equação renderizada abre as ações: isolar, derivar em relação a, integrar em relação a.
- **Bloco de resolução**: passos numerados, cada um com a equação (KaTeX), a justificativa, o selo e as condições; subpassos recolhíveis; chave completo/resumido; o termo alterado em cada passo vem destacado.
- **Tabela de variáveis**: sempre visível; símbolo, nome, valor, unidade (trocável), origem; avisos de faixa e de unidade na própria linha.
- **Biblioteca**: busca por nome, área, grandeza e hipótese; a ficha abre em painel com equação, hipóteses, demonstração, referência, exemplo e o botão “usar na folha”. Uma aba separada lista os pacotes de propriedades dos livros, com liga e desliga e a ordem de preferência (seção 7.5).
- **Arquivo**: novo, abrir, salvar, salvamento automático, desfazer e refazer; exportar para PDF (folha de estilo de impressão) e HTML autossuficiente. As folhas ficam no armazenamento do navegador (IndexedDB), no dispositivo do usuário; "baixar" e "abrir" trocam arquivos `.amsior` com o disco. Como limpar os dados do navegador apaga as folhas, a interface avisa e oferece baixar uma cópia.
- **Sem internet**: depois da primeira visita, tudo funciona desligado da rede; a barra de estado mostra quando há versão nova pronta.
- **Sobre**: autoria e propósito do projeto, licença (AGPL-3.0) e ligação para o código-fonte.
- **Acessibilidade**: operação completa por teclado; cada equação tem texto alternativo falado gerado da árvore; selos não dependem só de cor.
- **Textos**: nenhum texto de interface ou de justificativa no código; tudo em catálogos por idioma (`pt-BR` agora, `en` depois).

### 9.2 Ponte com o motor

A página fala com o trabalhador de cálculo por mensagens `{id, rota, dados}` e recebe `{id, ok}` ou `{id, erro}`. Não há estado entre chamadas de cálculo. Erros seguem um formato único: `codigo`, `mensagem`, `chave` (de tradução) e `detalhe`. No modo de desenvolvimento as mesmas rotas existem como HTTP sob `/api/v1`, e os testes comparam as duas vias.

| Rota | Entrada | Saída |
| --- | --- | --- |
| `textos` | Idioma | Textos da interface (chaves `ui.*`) |
| `glossario` | Nenhuma | Grandezas com unidade SI e suposições |
| `analisar` | LaTeX, tabela de símbolos | AmsiorExpr, símbolos novos, ambiguidades, tipo por variável |
| `isolar` | Equação, alvo, símbolos | Passos, resultado, ramos, certificados |
| `integrar` | Integral, símbolos, dependências | Passos, resultado, certificados |
| `derivar` | Expressão, variável, mantidas constantes | Passos, resultado, certificados |
| `edo` | Equação, função, variável, condição inicial | Classificação, passos, solução, certificados |
| `avaliar` | Folha ou subconjunto de blocos, valores | Valores com unidade, origem, avisos |
| `dimensional` | Equação, símbolos | Homogênea ou não, com o termo divergente |
| `propriedade` | Substância, origem, par de entrada, saídas | Valores, fase, fonte, referência |
| `interpolar` | Tabela, método, ponto | Valor, passos, avisos |
| `biblioteca`, `biblioteca/{id}` | Filtros | Índice; ficha completa |

Folhas e preferências não passam pelo motor: a página as lê e grava no armazenamento do navegador, e valida todo arquivo `.amsior` aberto antes de usá-lo (T-05).

Desempenho. O Python em WebAssembly é mais lento que o nativo e a primeira visita baixa o motor inteiro (dezenas de MB), que depois fica em cache. As metas do navegador são fixadas ao fim da fase 1C, com medições em máquina de aluno comum: tempo da primeira visita, tempo de abertura nas visitas seguintes, tempo de isolar nos exemplos e recálculo numérico de uma folha de 50 blocos. As metas da versão de desktop (isolar em menos de 1 s, recálculo em menos de 200 ms) ficam como referência do que se quer aproximar.

### 9.3 Animações (fase 4)

- **Demonstrações em vídeo**: uma cena Manim é gerada automaticamente a partir dos passos da ficha, transformando a equação de cada passo na do seguinte e exibindo a justificativa. Os vídeos são produzidos na máquina de desenvolvimento e publicados como arquivos; o navegador do aluno só os reproduz, e eles são baixados sob demanda, fora do cache de uso sem internet. Só fichas `verificada` ganham vídeo, e o vídeo guarda a versão da ficha que o gerou.
- **Gráficos interativos**: o bloco `grafico` e o campo `animacao` da ficha descrevem, de forma declarativa, a expressão, a variável do eixo e os parâmetros com controle deslizante. Os pontos são calculados pelo motor em lote e desenhados em Canvas.
- **Animações de conceito** (D-13): cenas para as fichas de conceito, como a mistura num CSTR, o perfil de conversão ao longo de um PFR e o gráfico de Levenspiel comparando CSTR e PFR, com controle deslizante de conversão. Todo número que a cena mostra vem do motor; a cena só desenha.

### 9.4 Design visual (D-11)

- **Sistemas escolhidos** (14/11/2026, prancha "Amsior — direções visuais da folha"): **D · Bancada com papel e tinta** como padrão e **H · Leitura longa** como alternativa. Mesma estrutura (trilho de ferramentas, passos em grade, tabela de variáveis com origem, barra de estado); D com Inter e STIX Two sobre papel creme e tinta azul; H com Atkinson Hyperlegible Next e Mono, letra maior, contraste de pelo menos 7:1 e papel quente de baixo brilho. Nas configurações: "Aparência" (D ou H) e "Modo" (claro, escuro, seguir o sistema). Impressão e PDF usam sempre D claro.

- **Princípio**: a tela serve à leitura da matemática. Pouco ruído, hierarquia clara, espaço generoso, nada que compita com a equação.
- **Sistema de design próprio**: cores, tipografia, espaçamento, raios e componentes definidos como *tokens* num só lugar e usados por toda a interface; nenhuma cor ou medida solta no código das telas.
- **Claro e escuro**: os dois temas são projetados juntos, com a mesma hierarquia, e não um derivado do outro. O padrão segue o tema do sistema, com troca manual; impressão e PDF usam sempre o claro.
- **Tipografia**: fonte de interface legível em tamanhos pequenos; matemática em KaTeX com a fonte que combina com o texto; algarismos tabulares nas tabelas de valores.
- **Contraste e acessibilidade**: texto com contraste mínimo de 4,5:1 (WCAG AA) nos dois temas, 3:1 para elementos gráficos; selos e estados nunca só por cor; foco de teclado sempre visível; animações reduzidas quando o sistema pede.
- **Revisão**: cada tela nova passa por revisão visual de Ruan nos dois modos antes de entrar numa versão.

## 10. Roteiro, riscos e pontos em aberto

Cada fase termina quando seus critérios de aceite passam na integração contínua; nenhuma fase começa com a anterior em vermelho.

### 10.1 Fases e critérios de aceite

| Fase | Entrega | Critérios de aceite |
| --- | --- | --- |
| 1A · Fundação | `expr`, `units`, `verify`, `i18n`; analisador de LaTeX restrito; versões travadas | Ida e volta LaTeX → árvore → LaTeX estável em 200 expressões; suíte “verificador sob ataque” reprova 100% dos passos errados e aprova 100% dos certos |
| 1B · Isolar | `rules`, `steps` (isolar), API, sistema de design (D-11), folha mínima com equação, resolução e tabela de variáveis, primeiro executável | Corpus de 60 equações: toda variável isolada com passos ou recusada corretamente; zero passo exibido sem certificado; testes de propriedade com 10 000 casos sem falha de V2; folha aprovada por Ruan nos modos claro e escuro |
| 1C · Navegador (D-14) | Motor no Pyodide dentro de um Web Worker; ponte de mensagens no lugar do servidor; service worker e instalação como PWA; publicação automática do site; tela "Sobre" com licença e código-fonte | Os 12 exemplos e o corpus de isolar dão no navegador exatamente os mesmos passos e certificados do Python de referência, comparados na integração contínua; estouro de tempo encerra e repõe o trabalhador; abre e calcula sem internet depois da primeira visita; nenhum pedido de rede leva dados do usuário (T-07); tempos de primeira visita, abertura e isolar medidos e registrados; folha aprovada por Ruan nos dois modos em Chrome ou Edge e em Firefox |
| 2 · Biblioteca | Esquema de ficha de equação e de conceito, glossário, hipóteses, fontes; as 5 fichas-modelo; as seções de Matemática e de Reatores (D-13); depois as demais | 5 fichas-modelo em `verificada` e 2 fichas-modelo de conceito (equação racional; CSTR) revisadas; toda etiqueta de tipo (D-12) leva a uma ficha de Matemática; corpus da biblioteca verde; cada ficha nova só entra com V1 a V6 aprovadas |
| 3A · Cálculo | Integrais, derivadas e EDOs com passos | Os 6 padrões da seção 4.3 e os 3 casos de EDO da 4.5 com passos e V3/V4 aprovadas; checagem de dependências cobre os casos de C\_p e de ∫V dP |
| 3B · Propriedades | `props`, `interp`, blocos de propriedade e interpolação; biblioteca de propriedades dos livros (esquema, importador, seletor de origem e primeiro pacote) | Pontos de verificação da IAPWS reproduzidos; avisos de fase, faixa e extrapolação testados; comparação interpolado × calculado funcionando; um pacote de livro completo transcrito, conferido e comparado com a origem calculada |
| 4 · Animações e distribuição | Gerador de cenas Manim, gráficos interativos, versão pública do site | Vídeo gerado sem ajuste manual para as 5 fichas-modelo; o site abre e funciona nas versões atuais de Chrome, Edge, Firefox e Safari sem instalar nada; exportação em PDF fiel à tela |

Modelos: Opus executa as fases; Fable revisa o desenho do verificador ao fim da 1A e as demonstrações delicadas da fase 2 (cúbicas de estado, aletas, efetividade-NTU, balanço de energia com reação).

### 10.2 Riscos

| Risco | Efeito | Tratamento |
| --- | --- | --- |
| `simplify` do SymPy inconclusivo em identidades verdadeiras | Passos corretos reprovados | Variantes de simplificação e certificado numérico de alta precisão (5.1) |
| Suposições de domínio incompletas | Raízes ou ramos errados | Suposições herdadas da grandeza; condições explícitas por regra; V2 por ramo |
| LaTeX do MathLive ambíguo | Expressão interpretada de forma diferente da intenção | Gramática restrita, pergunta em caso de dúvida, eco da interpretação antes de calcular |
| Passos corretos, mas pouco naturais | Valor didático baixo | Revisão de Ruan sobre o corpus; ajuste de prioridade das regras; modo resumido |
| Citação errada | Perda de credibilidade | D-05: nada de memória; conferência na última edição da fonte |
| Diferença entre valor do Amsior e tabela do livro | Aluno acha que o programa errou | Fonte e estado de referência visíveis; nota explicativa no bloco |
| Primeira visita pesada (Python e SymPy no navegador) | Aluno com internet lenta desiste antes de abrir | Tela de carregamento com progresso; cache pelo service worker; medir na fase 1C e cortar o que não for usado |
| Python em WebAssembly mais lento que o nativo | Passos demoram; tempo limite estoura em casos que passavam | Medir os exemplos e o corpus na fase 1C; rever o tempo limite com dados; aquecer o motor ao abrir |
| Resultado diferente entre navegador e Python de referência | Passo certificado num ambiente e não no outro | Mesmas versões de SymPy e mpmath nos dois; comparação automática do corpus na integração contínua |
| Bibliotecas de propriedades (CoolProp, chemicals) no navegador | Fase 3B sem a fonte prevista | Confirmar antes da fase 3B; se faltar, restringir o conjunto de fluidos ou trocar a fonte, com registro aqui |
| Dados só no navegador | Aluno limpa o navegador e perde as folhas | Aviso claro; baixar e abrir arquivo `.amsior`; salvamento automático com cópia para baixar |
| Crescimento de escopo | Fases que não fecham | Lista “fora do escopo” da seção 1; mudanças só pelo registro abaixo |

### 10.3 Pontos em aberto (não bloqueiam a fase 1)

- [ ] Acesso de Ruan à última edição de cada fonte (seção 8.1), com edição, ano e ISBN registrados em `_fontes.yaml` antes da fase 2.
- [x] Licença do código do Amsior: AGPL-3.0 (D-15, 15/11/2026). O conteúdo das fichas segue a mesma licença por ora.
- [ ] Avaliar uma licença de conteúdo (Creative Commons) para o texto didático das fichas, antes da fase 2.
- [x] Assinatura digital: deixa de ser necessária com a versão de navegador (D-14). Se o executável voltar, a SignPath Foundation assina projetos de código aberto sem custo.
- [ ] Endereço de publicação (GitHub Pages ou domínio próprio), a definir na fase 1C.
- [ ] Confirmar CoolProp e chemicals/thermo no Pyodide, antes da fase 3B.
- [ ] Quando reabrir o projeto a contribuições externas, e sob quais regras (D-15).
- [ ] Lista final das cerca de 50 fichas, a fechar no início da fase 2.
- [ ] Livro-base da seção de Matemática e lista final das fichas de conceito de Matemática e de Reatores (proposta na seção 8.7).
- [ ] Escopo exato da v1.1: solução numérica com método exibido, EDO linear de 2ª ordem, derivação implícita.

* [ ] Direitos de reprodução das tabelas de propriedades dos livros (seção 7.5), a resolver antes de distribuir pacotes a alunos. Com o repositório público (D-15), vale também antes de enviar qualquer tabela transcrita ao repositório.
* [ ] Original ou tradução: definir se a citação aponta para a última edição em inglês ou para a última em português, quando forem edições diferentes.
* [ ] Últimas edições de Levenspiel e de Treybal, a confirmar.

### 10.4 Registro de mudanças desta especificação

| Versão | Data | Mudança |
| --- | --- | --- |
| 1.0 | 13/11/2026 | Versão inicial, com as decisões D-01 a D-08 e T-01 a T-06; revisada no mesmo dia (ordem de dependência dos módulos, licenças, campos de símbolo e de passo, critério numérico e independência do verificador, etapa automática de V6). Versão 1.1, na mesma data: D-09 (última edição de cada fonte, seção 8.1) e D-10 (biblioteca de propriedades dos livros, seção 7.5). Versão 1.2, na mesma data, ao fechar a fase 1A: analisador próprio no lugar do Lark; operação declarada no passo; Lt e Le na árvore; substituições limitadas a restringe até a fase 2; zero compatível com qualquer dimensão (decisões 0001 e 0002 do repositório) |
| 1.3 | 14/11/2026 | Revisão do verificador pelo Fable (revisão 0001) e correções (decisão 0003): verificador sobre a árvore do Amsior, obrigações de domínio, avaliador numérico próprio e contraprova sempre, estratos de magnitude e cobertura de ramos, objetos opacos, relação reduzida a `equivalente` e `implica` com `sob_hipotese` calculado, certificado auditável, verificação de cadeia, `sympy.ask` retirado (seções 3.2, 5.1 e 5.3) |
| 1.4 | 14/11/2026 | D-11 (design visual como requisito, modos claro e escuro, seção 9.4); critério visual na fase 1B; `verify` antes de `rules` e `steps` na ordem de dependência (decisão 0004) |
| 1.5 | 14/11/2026 | Sistemas visuais D (padrão) e H; D-12 (tipo da equação, seção 4.7); D-13 (fichas de conceito, seções de Matemática e Reatores, seções 3.5, 8.7 e 9.3) |
| 1.6 | 15/11/2026 | D-14: o Amsior passa a rodar no navegador (D-02 revista; seções 2, 3.3, 9.1, 9.2 e 10; T-06 revista; T-07 nova; fase 1C nova; riscos de empacotamento trocados pelos da versão web). D-15: software livre sob AGPL-3.0, sem contribuições externas por enquanto. Decisão 0006 do repositório |
| 1.7 | 15/11/2026 | Fase 1C: tempo limite de 30 s provisório no navegador (seção 2, item 2), service worker e partida sem espera (itens 3 e 4); medições registradas na decisão 0006 |
