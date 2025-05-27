import os
from bot import Bot
from llmrag import LlmRag
from dotenv import load_dotenv


def main():
    load_dotenv()
    bot = Bot(llm=LlmRag(), config_file='../../config.json')
    bot.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()