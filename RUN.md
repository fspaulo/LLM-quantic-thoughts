## Configuração inicial — executar uma vez

Instale Python 3.11 e Ollama. Abra o Ollama e, no terminal dentro da pasta do projeto, execute:

```powershell
ollama pull qwen3:4b
ollama pull embeddinggemma:latest

py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py doctor
```

### Para usar vídeos e áudios — opcional

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-audio.txt
.\.venv\Scripts\python.exe app.py prepare-audio
```

## Adicionar conteúdos

Coloque PDFs, textos, vídeos ou áudios em `data/input/`. Pode organizar em subpastas.

Execute sempre que adicionar ou modificar arquivos:

```bash
.venv/Scripts/python.exe app.py index
```

Arquivos inalterados são pulados. Aguarde aparecer `Indexed` para cada arquivo processado.

## Rodar posteriormente

### Opção 1 — terminal

Abra o Ollama e execute na pasta do projeto:

```bash
.venv/Scripts/python.exe app.py chat --session medicine
```

Exemplo de pergunta:

> Responda em português: quais práticas os materiais sugerem para melhorar a pele?

Digite `/exit` para sair. Use a mesma sessão para continuar a conversa depois.

### Opção 2 — interface desktop

Para abrir a interface gráfica do app em Windows:

```powershell
.\.venv\Scripts\python.exe gui.py
```

Ou use o atalho:

```powershell
.\open-ui.bat
```

Na janela você pode:

- selecionar ou criar uma sessão
- mandar perguntas para o assistente
- indexar arquivos diretamente pela interface
- visualizar o histórico da sessão atual

Não precisa reinstalar, baixar os modelos ou indexar novamente se os arquivos não mudaram.