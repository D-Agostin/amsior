# Instalar o Python no Windows e rodar o Amsior

Passo a passo para quem ainda não tem o Python, ou não sabe qual versão tem.
O Amsior pede **Python 3.12 ou mais novo**.

## 1. Conferir se já existe um Python

Abra o **PowerShell** (tecla Windows, digite `PowerShell`, Enter) e rode:

```
py --list
```

- Se aparecer `3.12` ou `3.13` na lista, pule para o passo 3.
- Se aparecer só uma versão mais antiga, ou o comando não for reconhecido,
  siga o passo 2. Versões antigas podem ficar instaladas: o Windows aceita
  várias lado a lado.

## 2. Instalar o Python 3.13

**Opção A, pelo site:** baixe o instalador do Windows (64 bits) em
<https://www.python.org/downloads/windows/>. Na primeira tela do instalador,
marque **"Add python.exe to PATH"** e clique em **"Install Now"**.

**Opção B, pelo PowerShell:**

```
winget install -e --id Python.Python.3.13
```

Feche e abra o PowerShell de novo e confira:

```
py -3.13 --version
```

## 3. Instalar o Git (para quando o repositório estiver no GitHub)

```
winget install -e --id Git.Git
```

## 4. Preparar o ambiente do Amsior

No PowerShell, entre na pasta do projeto e crie um ambiente isolado:

```
cd "$env:USERPROFILE\Desktop\AMSIOR"
py -3.13 -m venv .venv
```

O ambiente não precisa ser "ativado". Em vez de rodar o `Activate.ps1`, que o
Windows bloqueia por padrão, chame direto o Python que está dentro dele. Para
não digitar o caminho toda vez, guarde-o numa variável (vale até você fechar a
janela; ao abrir outra, rode a linha de novo):

```
$py = "$env:USERPROFILE\Desktop\AMSIOR\.venv\Scripts\python.exe"
& $py --version
```

Assim nenhuma configuração de segurança do Windows é alterada. Instale as
dependências nas versões travadas:

```
cd motor
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements-lock.txt
& $py -m pip install -e . --no-deps
```

## 5. Rodar os testes e o relatório de aceite

```
& $py -m pytest
& $py -m mypy
& $py ..\ferramentas\aceite_1a.py
```

O esperado é todos os testes passando e o relatório com dois `[OK]`.

## 6. (Opcional) Protótipo do instalador

```
cd ..\ferramentas\empacotamento
& $py -m pip install -r requirements-empacotamento.txt
& $py -m PyInstaller --noconfirm ola_amsior.spec
.\dist\ola_amsior.exe
```

O executável imprime um relatório em JSON, com uma linha por biblioteca. Todas
precisam dizer `"ok": true`. O arquivo tem cerca de 150 MB; o tamanho do
instalador final será otimizado na fase 4.

## Se algo der errado

Copie a mensagem de erro inteira e mande na conversa. As falhas mais comuns
são a versão errada do Python (confira com `& $py --version`) e o antivírus
bloqueando o `ola_amsior.exe` recém-gerado.
