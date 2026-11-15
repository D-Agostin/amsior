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
