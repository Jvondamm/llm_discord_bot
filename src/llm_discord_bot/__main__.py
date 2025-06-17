import os
from pathlib import Path
from dotenv import load_dotenv
from llm_discord_bot.bot import Bot
from llm_discord_bot.llmrag import LlmRag


def main():
    load_dotenv()
    config_file = os.getenv("CONFIG_FILE")
    discord_token = os.getenv("DISCORD_TOKEN")
    if config_file is None:
        raise EnvironmentError("Could not find environment variable for `CONFIG_FILE`, exiting")
    elif discord_token is None:
        raise EnvironmentError(f"Could not find environment variable for `DISCORD_TOKEN`, exiting")
    else:
        bot = Bot(llm=LlmRag(), config_file=os.getenv)
        bot.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()