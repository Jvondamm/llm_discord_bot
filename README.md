### Installation
Download the .whl file from the [releases](https://github.com/Jvondamm/llm_discord_bot/releases), 
then install with uv (recommended, it's just [faster than pip](https://docs.astral.sh/uv/#:~:text=%E2%9A%A1%EF%B8%8F%2010%2D100x%20faster%20than%20pip)):

```commandline
uv pip install llm_discord_bot-x.x.x.whl
```
but pip still works:
```commandline
pip install llm_discord_bot-x.x.x.whl
```

*There are no plans as of yet to add to pypi unless this project is deemed package-worthy*

---

### Configuration
The bot requires: 
- [Huggingface User Access Token](https://huggingface.co/login?next=%2Fsettings%2Ftoken) to access Huggingface models
- [Discord Bot Token](https://www.writebots.com/discord-bot-token/) to authenticate the bot
- [Discord Guild (Server) ID](https://cybrancee.com/learn/knowledge-base/how-to-find-a-discord-guild-id/) that the bot will join 

and optionally takes:

- [Huggingface Model Path](https://huggingface.co/models) for the model that will be used, defaults to `meta-llama/Llama-3.2-3B-Instruct`
- Index (Database) Path for storing documents for RAG, defaults to `~/index`
- Llm Config File Path to set the system prompt, temperature, and chat history, defaults are in the `config.json`

These can be added to your `$PATH`, or more simply stored in a `.env` file like the example in the repo. 
The file can reside in any parent or child directory of the installation directory.
---
### Execution
```commandline
ldbot
```
---
### Developing
Contributions are welcome, feel free to open PRs, 
but be sure to explain the intended change and format/lint the code beforehand.

```commandline
git clone https://github.com/Jvondamm/llm_discord_bot
cd llm_discord_bot
uv run python -m llm_discord bot
```
To install the optional dependencies
```commandline
uv pip install [dev]
```

Before submitting a PR: 
1. Lint and format the code with ruff's `check` and `format` (See ruff's [docs](https://docs.astral.sh/ruff/) for how neat it is)
    ```commandline
    uvx ruff check
    uvx ruff format
    ```
2. Ensure a package can be built and it runs with `ldbot`
    ```commandline
    uv build
    ```
