import os
from pathlib import Path
from dotenv import load_dotenv
from llm_discord_bot.bot import Bot
from llm_discord_bot.llmrag import LlmRag


def main():
    load_dotenv()
    bot = Bot(llm=LlmRag(), config_file=Path(__file__).parent.parent / 'config.json')
    bot.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()