# Amsior

Calculadora e biblioteca didática de equações para engenharia química. Cada
cálculo mostra o raciocínio passo a passo, e nenhum passo aparece sem ter sido
verificado por máquina.

> Idealizado por Ruan D'Agostin como ferramenta livre para fomento à ciência e
> à engenharia, com fins educacionais e gratuitos.

## Estado

Em desenvolvimento; ainda não há versão pública para uso.

- **Fase 1A (fundação), concluída:** árvore de expressões, analisador de LaTeX,
  unidades e verificador. Ida e volta LaTeX em 232 de 232 expressões; o
  verificador aprova 44 de 44 passos certos e reprova 73 de 73 passos errados.
- **Fase 1B (isolar variável), concluída:** motor que isola uma variável com
  passos certificados, primeira tela (equação, resolução e tabela de
  variáveis) e dois sistemas visuais com modo claro e escuro, aprovados na
  revisão visual.
- **Fase 1C (navegador), concluída:** o Amsior roda inteiro no
  navegador, sem instalação, e dá as mesmas respostas do Python nativo.
  Funciona sem internet depois da primeira visita e pode ser instalado como
  aplicativo pelo navegador. Versão de teste em
  <https://d-agostin.github.io/amsior/>. Veja a
  [decisão 0006](docs/decisoes/0006-navegador-e-software-livre.md).
- **Fase 2 (biblioteca), em andamento:** esquema das fichas de equação e de
  conceito conferido pelos testes, registro de fontes, vocabulário de
  hipóteses e as 28 fichas de conceito de Matemática e de Reatores criadas
  na ordem da especificação. Onze já estão escritas, em revisão, e aparecem no
  painel da biblioteca do site: em Matemática, expressões algébricas, equações
  do 1º e do 2º grau, racional, irracional e equivalência e implicação; em
  Reatores, conversão e tempo espacial, batelada, CSTR, PFR e o gráfico de
  Levenspiel. Os exemplos de cada ficha são refeitos pelo motor nos testes.
  O motor passou a resolver equações do 2º grau com passos e a descartar
  raízes estranhas com o motivo.
  As cinco fichas-modelo de equação, de Termodinâmica, estão escritas e
  verificadas por máquina: gás ideal, 1ª lei para sistema fechado, calor
  sensível com C_p(T), Clausius-Clapeyron e Antoine. Cada passo da
  demonstração é certificado, cada variável é isolada com passos e o exemplo
  é conferido contra uma fonte independente (CoolProp ou tabelas NIST-JANAF).
  No site, cada uma mostra a demonstração com selos e abre na folha.

## O que existe

- `motor/amsior/expr`: árvore de expressões (AmsiorExpr), analisador do LaTeX
  restrito, impressão canônica, JSON e ponte com o SymPy.
- `motor/amsior/units`: glossário de grandezas, análise dimensional simbólica e
  conversão de unidades.
- `motor/amsior/verify`: certificação de cada passo e verificação da solução.
- `motor/amsior/rules` e `motor/amsior/steps`: regras e estratégia para isolar
  uma variável, com classificação do tipo de equação.
- `motor/amsior/api`: contrato de pedidos entre a interface e o motor.
- `motor/amsior/i18n`: catálogo de textos (pt-BR).
- `interface/`: interface em React e TypeScript.
- `biblioteca/_glossario.yaml`: 60 grandezas com unidade SI e suposições.
- `motor/amsior/biblioteca`: leitura e validação das fichas, e verificação
  das fichas de equação (demonstração, corpus e exemplo).
- `biblioteca/_fontes.yaml`: livros-base e de apoio, na última edição, com o
  estado da conferência.
- `biblioteca/_hipoteses.yaml`: vocabulário controlado de hipóteses.
- `biblioteca/matematica/` e `biblioteca/reatores/`: fichas de conceito.
- `biblioteca/termodinamica/`: fichas de equação.

## Como rodar (desenvolvimento)

Motor (Python 3.12 ou mais novo; veja
[docs/instalar-python-windows.md](docs/instalar-python-windows.md)):

```
cd motor
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
python -m mypy
python -m pytest
```

Site (Node 22 e, para a partida mais rápida, um Python 3.14 para o bytecode):

```
python ferramentas/web/montar_motor.py
cd interface
npm ci
npm test
npm run build
npx vite preview
```

Com o site aberto, o endereço terminado em `#medir` mostra quanto o navegador
baixou e quanto o motor leva para isolar cada exemplo.

## Documentos

- [Especificação](docs/especificacao.md)
- [Gramática do LaTeX aceito](docs/gramatica.md)
- [Registros de decisão](docs/decisoes/)

## Licença e contribuições

Copyright (c) 2026 Ruan D'Agostin.

O Amsior é software livre sob a [GNU Affero General Public License, versão 3](LICENSE)
(AGPL-3.0). Você pode usar, estudar, copiar e modificar; quem distribuir ou
hospedar uma versão modificada tem de oferecer o código-fonte sob a mesma
licença. O programa é oferecido sem nenhuma garantia. As bibliotecas de
terceiros mantêm as suas próprias licenças.

O conteúdo didático da [biblioteca](biblioteca/) (fichas, figuras, hipóteses e
fontes) está sob a [Creative Commons Atribuição-CompartilhaIgual 4.0](biblioteca/LICENSE)
(CC BY-SA 4.0). O livro-base da seção de Matemática é o livro aberto
*Pré-cálculo: um livro colaborativo*, do [REAMAT](https://www.ufrgs.br/reamat/PreCalculo)
(UFRGS), sob a mesma licença.

O projeto não aceita contribuições externas por enquanto. Veja
[CONTRIBUTING.md](CONTRIBUTING.md).
