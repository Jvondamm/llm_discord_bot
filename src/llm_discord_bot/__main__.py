import os
from bot import Bot
from llm import Llm
from dotenv import load_dotenv


def main():
    load_dotenv()
    Bot(llm=Llm(os.getenv("MODEL")), config_file='config.json')


if __name__ == "__main__":
    main()