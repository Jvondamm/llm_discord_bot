import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from datasets import load_dataset
import pandas as pd
from tqdm.notebook import tqdm
from langchain.docstore.document import Document as LangchainDocument


logger = logging.getLogger("DB")
# region constants
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
DEFAULT_DATASET_SRC = '../../db'
# endregion

pd.set_option("display.max_colwidth", None)
ds = load_dataset("OpenAssistant/oasst1")
RAW_KNOWLEDGE_BASE = [LangchainDocument(page_content=doc["text"], metadata={"source": doc["source"]}) for doc in
                      tqdm(ds)]


# region classes
class Database:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # The maximum number of characters in a chunk: we selected this value arbitrarily
            chunk_overlap=100,  # The number of characters to overlap between chunks
            add_start_index=True,  # If `True`, includes chunk's start index in metadata
            strip_whitespace=True,  # If `True`, strips whitespace from the start and end of every document
            separators=MARKDOWN_SEPARATORS,
        )

# endregion
