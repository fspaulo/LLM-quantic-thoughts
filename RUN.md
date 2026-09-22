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

Abra o Ollama e execute na pasta do projeto:

```bash
.venv/Scripts/python.exe app.py chat --session medicine
```

Exemplo de pergunta:

> Responda em português: quais práticas os materiais sugerem para melhorar a pele?

Digite `/exit` para sair. Use a mesma sessão para continuar a conversa depois.

Não precisa reinstalar, baixar os modelos ou indexar novamente se os arquivos não mudaram.