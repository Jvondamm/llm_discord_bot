Installation:
```commandline
uv pip install ./
```
Configuration:

Configure your Discord Token, Guild ID, Huggingface LLM model, Index (database) Directory, and optional config file
```commandline
vim ~/.env
```

---
Execution:
```commandline
ldbot
```

Developing:
```commandline
git clone https://github.com/Jvondamm/llm_discord_bot
cd llm_discord_bot
uv 
uv run python -m llm_discord bot
```

Packaging:
```commandline
uv build
```
