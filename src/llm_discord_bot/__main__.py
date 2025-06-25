import os
from dotenv import load_dotenv
from llm_discord_bot.bot import Bot
from llm_discord_bot.llmrag import LlmRag
from huggingface_hub import login


def main():
    load_dotenv()
    config_file = os.getenv("CONFIG_FILE")
    discord_token = os.getenv("DISCORD_TOKEN")
    huggingface_token = os.getenv("HUGGINGFACE_TOKEN")
    if discord_token is None:
        raise EnvironmentError("Could not find environment variable for `DISCORD_TOKEN`, exiting")
    elif huggingface_token is None:
        raise EnvironmentError("Could not find environment variable for `HUGGINGFACE_TOKEN`, exiting")

    login(token=huggingface_token)
    bot = Bot(llm=LlmRag(llm_model_name=os.getenv("MODEL")), config_file=config_file)
    bot.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()
