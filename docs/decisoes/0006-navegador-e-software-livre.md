# 0006 — O Amsior roda no navegador e é software livre

- Data: 15/11/2026
- Estado: aceita
- Detalha: especificação v1.6, decisões D-02 (revista), D-14 e D-15; seções 2, 9 e 10

## Contexto

O primeiro `Amsior.exe` (decisão 0005) passou no autoteste da integração
contínua, mas foi bloqueado no computador do autor pelo Controle Inteligente
de Aplicativos do Windows 11. Esse recurso barra executáveis sem assinatura
digital e sem reputação, e não oferece ao usuário a opção de executar assim
mesmo. O mesmo aconteceria com qualquer aluno que tenha o recurso ligado.

Assinar o executável exige um certificado de assinatura de código. O serviço
da Microsoft não atende pessoas físicas no Brasil; as alternativas são um
certificado pago ou a assinatura gratuita da SignPath Foundation, que exige
projeto de código aberto com repositório público.

## Decisões

1. **Navegador no lugar do executável (D-14).** O Amsior vira um site
   estático. O motor continua sendo o pacote Python `amsior`, executado pelo
   Pyodide dentro de um Web Worker; a interface React é a mesma. Um site não
   precisa de assinatura, não exige instalação e funciona em qualquer sistema.

2. **Mesmo contrato, outro transporte.** As rotas de `amsior.api.servico`
   (`executar(rota, dados)`) não mudam. Na página, `api.ts` troca o `fetch`
   por mensagens ao trabalhador. O token de sessão e a porta deixam de
   existir; as preferências voltam ao armazenamento do navegador, porque o
   endereço passa a ser fixo.

3. **Isolamento do cálculo (T-06).** O processo separado vira um Web Worker.
   Ao estourar o tempo, a página encerra o trabalhador e cria outro.

4. **Privacidade (T-07).** Sem servidor de cálculo, nada do que o usuário
   digita sai do dispositivo. Sem contas e sem telemetria.

5. **Servidor local só para desenvolvimento.** `amsior.api.app` e
   `amsior.janela` ficam como modo de desenvolvimento e como referência: a
   integração contínua compara as respostas do navegador com as do Python
   nativo. O executável deixa de ser entregue; o empacotamento permanece no
   repositório até a fase 1C terminar e depois é removido ou arquivado.

6. **Software livre (D-15).** Licença AGPL-3.0 (identificador SPDX
   `AGPL-3.0-only`), escolhida pelo autor: quem distribuir ou hospedar uma
   versão modificada tem de oferecer o código. O projeto não aceita
   contribuições externas por enquanto.

## O que ainda não foi medido

Esta decisão foi tomada antes da prova de conceito. A fase 1C (especificação,
seção 10.1) existe para confirmar, com números:

- o tamanho e o tempo da primeira visita (Python, SymPy, mpmath e pint);
- o tempo de isolar cada exemplo e o corpus no navegador, contra o tempo
  limite de 10 s;
- que os passos e os certificados saem idênticos aos do Python nativo;
- se CoolProp e chemicals/thermo rodam no Pyodide (necessário só na fase 3B).

Se algum desses pontos falhar, a mudança é registrada na seção 10.4 da
especificação antes de seguir.

## Prova de conceito (15/11/2026)

O motor já roda no navegador, num Web Worker com Pyodide 314.0.8 (Python 3.14.2),
e a interface fala com ele por mensagens. Tudo é servido pelo próprio site.

**Mesmas respostas.** Os 305 pedidos de teste (textos, glossário, os 12 exemplos
e todas as 291 variáveis do corpus de isolar) dão respostas idênticas no
Pyodide e no Python nativo, campo a campo: passos, LaTeX, justificativas e
certificados. A integração contínua repete a comparação a cada envio, e o
site só é publicado se não houver diferença.

**Medições** (Chrome sem interface gráfica e Node, na máquina de desenvolvimento):

| Medida | Valor |
| --- | --- |
| Tela aberta (antes do motor) | 0,3 s |
| Partida do motor (Python, bibliotecas, glossário) | 2,7 s com bytecode pronto; 5,3 s sem |
| Download na primeira visita | 24,5 MB sem compressão (Python 9,2 MB, biblioteca padrão 2,4 MB, motor 10,5 MB, interface e fontes); cerca de 17 MB se o servidor comprimir o Python e o JavaScript. Nas visitas seguintes, o navegador reaproveita o cache |
| Do endereço digitado ao motor pronto (servidor local) | 4,2 s |
| Isolar, mediana do corpus | 0,11 s no navegador; 0,06 s nativo (1,8 vez mais lento) |
| Isolar, os 12 exemplos | de 0,02 s a 1,3 s |
| Isolar, pior caso do corpus | 12,1 s no navegador (Fenske, α); 6,4 s nativo |

**Decisões tomadas com esses números:**

1. **Bytecode pronto.** As bibliotecas de terceiros vão como `.pyc` compilados
   por um CPython 3.14 (mesmo número mágico do Pyodide). A partida cai de 5,3 s
   para 2,7 s; o motor cresce de 5 MB para 10,5 MB, baixados uma vez só. Sem
   `-O`: tirar asserts e docstrings encolheria o zip, mas muda o comportamento
   das bibliotecas.
2. **Tempo limite de 30 s no navegador**, provisório. Com 10 s, cinco variáveis
   do corpus (Fenske, capacitância global, Bernoulli) estourariam no navegador,
   embora passem no nativo. O valor definitivo sai das medições em máquinas de
   aluno.
3. **A tela não espera o motor.** Textos e glossário são gerados na montagem
   (`dados.json`); a interface abre na hora e os pedidos esperam na fila até o
   motor ficar pronto.
4. **PyYAML fora do navegador.** O glossário vai em JSON; o motor lê YAML ou
   JSON pela extensão.

Falta, para fechar a fase 1C: funcionar sem internet (service worker),
instalação como aplicativo, a tela "Sobre", medições em máquinas de aluno e a
revisão visual de Ruan.
