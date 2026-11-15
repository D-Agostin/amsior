# 0005 — Primeira tela, API local e executável (fase 1B)

- Data: 15/11/2026
- Estado: aceita
- Detalha: especificação, seções 2, 9.2 e 9.4; decisões D-11 e D-12

## Decisões

1. **Interface em React com estado em Zustand.** A interface edita, mostra e
   pede; nenhuma matemática roda nela. Cada pedido leva um número de ordem e
   a resposta de um pedido antigo (a equação já mudou) é descartada.

2. **Textos só do catálogo.** As chaves `ui.*` ficam em `pt-BR.json` e chegam
   pela rota `GET /api/v1/textos`. Um teste do motor varre `interface/src` e
   exige que toda chave usada exista. Trechos de matemática nos textos vêm
   marcados com `\( \)` e são desenhados com KaTeX.

3. **KaTeX com STIX Two.** As fórmulas usam a fonte de matemática dos tokens
   (`--fonte-mat`); os símbolos que a STIX não traz no subconjunto embutido
   (≥, ≤, √) caem para a fonte do KaTeX. Passos e resultado usam o estilo de
   exibição (frações em tamanho cheio) e não quebram linha: uma equação longa
   rola na própria célula.

4. **Editor MathLive local.** Fontes copiadas para `public/mathlive` (sem
   internet), vírgula decimal, menu desligado. O analisador passou a ler
   `Ae^{x}` como `A·exp(x)`: antes, o `e` colado numa palavra virava símbolo.

5. **Configurações em popover, não em diálogo modal.** Com o diálogo modal a
   página fica inerte; se a aparência muda nesse estado, o MathLive deixa de
   receber teclas até ser recriado (reproduzido com o Chrome, D → H). O
   popover fecha com Esc ou clicando fora e não deixa nada inerte.

6. **Preferências no servidor.** A porta muda a cada partida e o navegador
   separa o armazenamento por porta; por isso aparência, modo e nível ficam em
   `preferencias.json` na pasta do usuário (`%APPDATA%\Amsior`), pela rota
   `GET/PUT /api/v1/preferencias`. O armazenamento local guarda só uma cópia
   para a primeira pintura. Impressão sai sempre em D claro.

7. **Tipo da equação na resolução (D-12).** O tipo aparece numa faixa logo
   abaixo do título da resolução e na dica de cada botão "Isolar". A ligação
   com a ficha de Matemática entra com a biblioteca.

8. **Exemplos testados.** O painel de exemplos lê `interface/src/dados/exemplos.json`;
   um teste do motor isola o alvo de cada um e exige todos os passos
   certificados, e o catálogo precisa ter o nome e a área de cada exemplo.

9. **Tempo limite de 10 s**, como na seção 2. O exemplo mais lento leva
   0,9 s em Linux.

10. **Executável com autoteste.** `amsior.janela` sobe o servidor em
    `127.0.0.1`, porta livre, token sorteado, e abre a janela (pywebview). Com
    `--autoteste`, faz os pedidos da primeira tela (interface, textos,
    glossário, analisar, isolar com certificado) e sai com 0 só se tudo
    responder. O CI gera `Amsior.exe` no Windows e roda o autoteste antes de
    publicar o artefato. O autoteste já pegou um defeito: com o motor
    instalado em modo editável, o PyInstaller não levava os catálogos de
    texto; agora vão explícitos no `amsior.spec`.

11. **Motor: lado zero não é multiplicado.** Ao eliminar o denominador de
    `… = 0`, o lado direito continua `0`, e o fator aparece como o usuário o
    escreveu (`1 + kτ`, não `τk + 1`). O CSTR de 1ª ordem caiu de 12 para 10
    passos, sem o "subtrair 0(τk + 1)".

## Pendências conhecidas

- O agrupamento no alvo ainda mostra `(−Xk + k)τ + (−X)` antes de simplificar;
  vale um acabamento próprio.
- Clicar fora do popover para fechá-lo não leva o foco ao editor: é preciso
  um segundo clique (comportamento padrão do popover no Chromium).
