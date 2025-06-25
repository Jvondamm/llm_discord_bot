DATASET_LIST = "datasets.json"
DEFAULT_INDEX = "index"
MARKDOWN_SEPARATORS = [
    "\n#{1,6} ",
    "```\n",
    "\n\\*\\*\\*+\n",
    "\n---+\n",
    "\n___+\n",
    "\n\n",
    "\n",
    " ",
    "",
]
RAG_PROMPT = [
    {
        "role": "system",
        "content": """{identity}

Give a comprehensive answer to the question using, but not limited to, the information in the context.
Respond only to the question asked, response should be concise and relevant to the question.
If the answer cannot be deduced from the context, say that the local database doesn't have relevant information, and provide an answer to the question using your own knowledge.""",
    },
    {
        "role": "user",
        "content": """Context:
{context}
---
Now here is the question you need to answer.

Question: {query}""",
    },
]
PROMPT = [
    {
        "role": "system",
        "content": """{identity}

        Give a comprehensive answer to the question. 
        Respond only to the question asked, response should be concise and relevant to the question.""",
    },
    {
        "role": "user",
        "content": """Question: {query}""",
    },
]
DEFAULT_CONFIG = {
    "identity": "You are a helpful assistant named llama, you are an expert in many subjects and provide carefully researched, thoughtful answers",
    "temperature": 0.7,
    "history_lines": 5,
}
