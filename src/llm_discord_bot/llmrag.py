import logging
import os
import shutil
import json
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from typing import List
import torch
from transformers import AutoTokenizer, pipeline, BitsAndBytesConfig, AutoModelForCausalLM
from datasets import load_dataset
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from llm_discord_bot.constants import RAG_PROMPT, PROMPT, MARKDOWN_SEPARATORS, DEFAULT_INDEX, DATASET_LIST

# region logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLM_RAG")
# endregion

pd.set_option("display.max_colwidth", None)
load_dotenv()

# region classes
class LlmRag:
    def __init__(
        self,
        llm_model_name: str = "meta-llama/Llama-3.2-3B-Instruct",
        embedding_model_name: str = "thenlper/gte-small",
    ):
        self.embedding_model_name = embedding_model_name
        self.embedding_model = self._initialize_embedding_model(embedding_model_name)
        self.database_path, self.loaded_index, self.db_entries = self._initialize_database(embedding_model=self.embedding_model)
        self.llm = self._initialize_llm(model_name=llm_model_name)


    @staticmethod
    def _initialize_embedding_model(model_name):
        """
        Load Huggingface embedding model

        :param model_name: THe Huggingface model to use for embeddings
        """
        logger.info(f"Loading embedding {model_name=}")
        return HuggingFaceEmbeddings(
            model_name=model_name,
            multi_process=True,
            model_kwargs={"device": "cuda"},
            encode_kwargs={"normalize_embeddings": True}
        )

    @staticmethod
    def _initialize_database(embedding_model: HuggingFaceEmbeddings,
                             ) -> (FAISS, dict[str]):
        """
        Load database if it exists, else create a new one

        :param embedding_model: Huggingface model to convert raw data to vectors
        """
        try:
            index_path = Path(os.getenv("INDEX_PATH"))
        except Exception as e:
            raise FileNotFoundError("INDEX_PATH does not exist as an environment variable, ensure it is defined in your .env") from e
        index_path.mkdir(parents=True, exist_ok=True)
        local_index, dataset_list = None, {}
        if os.path.exists(index_path / Path(DEFAULT_INDEX + ".faiss")):
            logger.info(f"Loading index from {index_path}")
            local_index = FAISS.load_local(folder_path=str(index_path),
                                    embeddings=embedding_model,
                                    allow_dangerous_deserialization=True)  # Ensures we trust the index source
        else:
            logger.warning(f"No local index found in {index_path / Path(DEFAULT_INDEX + ".faiss")}")
        if os.path.exists(index_path / Path(DATASET_LIST)):  # list of datasets in the index
            with open(index_path / Path(DATASET_LIST), 'r') as f:
                dataset_list = json.load(f)
        if local_index is not None and len(dataset_list) == 0:
            logger.warning(f"Unknown datasets in the database, will not be able to track them going forward")
        return index_path, local_index, dataset_list

    def _initialize_llm(self, model_name):
        """
        Quantize model, load it, and apply default and rag chat templates

        :param model_name: Huggingface name of the model
        """
        logger.info("Initializing bitsandbytesconfig...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

        logger.info(f"Loading model from {model_name=}")
        model = AutoModelForCausalLM.from_pretrained(model_name, quantization_config=bnb_config)
        logger.info(f"Loading tokenizer from {model_name=}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.rag_prompt = tokenizer.apply_chat_template(RAG_PROMPT, tokenize=False, add_generation_prompt=True)
        self.prompt = tokenizer.apply_chat_template(PROMPT, tokenize=False, add_generation_prompt=True)

        return pipeline(
            task="text-generation",
            model=model,
            tokenizer=tokenizer,
            do_sample=True,
            max_new_tokens=500,
            temperature=0.2,
            repetition_penalty=1.1,
            return_full_text=False,
        )

    @staticmethod
    def split_documents(
            chunk_size: int,
            documents: List[Document],
            tokenizer_name: str
    ) -> List[Document]:
        """
        Split documents into chunks of maximum size `chunk_size` tokens and return a list of documents

        :param chunk_size: Maximum chunk size in tokens
        :param documents: The loaded data to split
        :param tokenizer_name: Pretrained model for tokenizing
        """
        logger.info(f"Initializing text splitter with {tokenizer_name=}...")
        text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
            AutoTokenizer.from_pretrained(tokenizer_name),
            chunk_size=chunk_size,
            chunk_overlap=int(chunk_size / 10),
            add_start_index=True,
            strip_whitespace=True,
            separators=MARKDOWN_SEPARATORS,
        )

        logger.info(f"Processing docs in knowledge base...")
        docs_processed = text_splitter.split_documents(documents)

        # Remove duplicates
        unique_texts = {}
        docs_processed_unique = []
        for doc in docs_processed:
            if doc.page_content not in unique_texts:
                unique_texts[doc.page_content] = True
                docs_processed_unique.append(doc)

        return docs_processed_unique

    def merge_dataset_to_db(self,
                            huggingface_dataset: str,
                            split: str,
                            column: str):
        """
        Adds Huggingface dataset to database

        :param huggingface_dataset: Huggingface dataset path
        :param split: Dataset split name to use
        :param column: Dataset column name to use
        """
        logger.info(f"Loading dataset `{huggingface_dataset}` on {split=} with {column=}")
        ds = load_dataset(path=huggingface_dataset, split=split, num_proc=8)
        if column not in ds[0]:
            return f"Column `{column}` not in `{huggingface_dataset}`, valid columns are {ds[0].keys()}"
        loaded_ds = [Document(page_content=doc[column]) for doc in ds]
        self.merge_to_db(huggingface_dataset, ds.dataset_size, loaded_ds)


    def merge_to_db(self,
                    data_name: str,
                    data_size: float,
                    data: List[Document]):
        """
        Merges the file or dataset into the database

        :param data_name: The filename or name of the dataset
        :param data_size: The size of the data in bytes
        :param data: The data as a list of Langchain Document(s)
        """
        docs_processed = self.split_documents(chunk_size=512,
                                              documents=data,
                                              tokenizer_name=self.embedding_model_name)

        logger.info(f"Creating vector store of {data_name}")
        new_index_store = FAISS.from_documents(
            docs_processed, self.embedding_model, distance_strategy=DistanceStrategy.COSINE
        )
        if self.loaded_index is not None:
            self.loaded_index.merge_from(new_index_store)
            self.loaded_index.save_local(self.database_path)
        else:
            new_index_store.save_local(self.database_path)
            self.loaded_index = new_index_store
        self.db_entries[data_name] = round(data_size / 1e6, 2)  # store in MB
        with open(self.database_path / Path(DATASET_LIST), 'w', encoding='utf-8') as f:
            json.dump(self.db_entries, f, ensure_ascii=False, indent=4)


    def drop_database(self):
        """Deletes the index and dataset list"""
        index_path = Path(os.getenv("INDEX_PATH"))
        for filename in os.listdir(index_path):
            file_path = os.path.join(index_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    logger.info(f"Deleting file {file_path}")
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    logger.info(f"Deleting directory {file_path}")
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.info(f"Failed to delete {file_path}. Reason: {e}")
        self.loaded_index = None
        for data in self.db_entries.keys():
            logger.info(f"Deleting {data}")
        self.db_entries = None


    def response(
        self,
        query: str,
        context: str,
        identity: str,
        num_retrieved_docs: int = 30,
        num_docs_final: int = 5,
        rag: bool = False
    ) -> tuple[str, List[Document] | None]:
        """
        Generate a llm response

        :param query: Query for the llm
        :param context: Discord channel history
        :param identity: llm configured identity
        :param num_retrieved_docs: Maximum number of docs to retrieve from the RAG database
        :param num_docs_final: Maximum number of docs presented as context to the llm
        :param rag: Whether to add database information into the prompt
        """
        relevant_docs = None
        if rag:
            if self.loaded_index is None:
                logger.error("Did not provide any datasets to initialize local index")
                return "Couldn't reply with RAG: Database is empty.\nPopulate the database with Huggingface datasets or upload documents", None
            if not query:
                logger.warning(f"Empty query, cannot query database")
            else:
                logger.info(f"Retrieving documents using {query=}\n")
                relevant_docs = self.loaded_index.similarity_search(query=query, k=num_retrieved_docs)
                # relevant_docs = [doc.page_content for doc in relevant_docs]  # Keep only the text
                # relevant_docs = relevant_docs[:num_docs_final]

                # Build the final prompt
                context += "\nExtracted documents:\n"
                for i, doc in enumerate(relevant_docs):
                    if i < num_docs_final:
                        context += f"\n:::Document {doc.title}:::\n{doc.page_content}"
                    else:
                        break
                # context += "".join([f"\n:::Document {str(i)}:::\n" + doc for i, doc in enumerate(relevant_docs)])

            prompt = self.rag_prompt.format(identity=identity, query=query, context=context)
        else:
            prompt = self.prompt.format(identity=identity, query=query, context=context)

        logger.info(f"PROMPT:\n{prompt}")
        answer = self.llm(prompt)[0]["generated_text"]
        logger.info(f"ANSWER:\n{answer}")

        return answer, relevant_docs
    # endregion
