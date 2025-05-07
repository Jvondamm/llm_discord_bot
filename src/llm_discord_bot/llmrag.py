import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from datasets import load_dataset
import pandas as pd
from tqdm.notebook import tqdm
from langchain.docstore.document import Document as LangchainDocument
from typing import List
import torch
from transformers import AutoTokenizer, pipeline, BitsAndBytesConfig, AutoModelForCausalLM
# from ragatouille import RAGPretrainedModel
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_community.vectorstores import FAISS
from langchain_community.llms import HuggingFacePipeline
from langchain_huggingface import HuggingFaceEmbeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLM_RAG")

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
# DEFAULT_DATASET_SRC = '../../db'
# endregion

pd.set_option("display.max_colwidth", None)
ds = load_dataset(path="pszemraj/fineweb-1k_long", split="train")
RAW_KNOWLEDGE_BASE = [LangchainDocument(page_content=doc["text"]) for doc in
                      tqdm(ds)]


PROMPT = [
    {
        "role": "system",
        "content": """Using the information contained in the context,
give a comprehensive answer to the question.
Respond only to the question asked, response should be concise and relevant to the question.
Provide the number of the source document when relevant.
If the answer cannot be deduced from the context, do not give an answer.""",
    },
    {
        "role": "user",
        "content": """Context:
{context}
---
Now here is the question you need to answer.

Question: {question}""",
    },
]



# region classes
class LlmRag:
    def __init__(
        self,
        llm_model_name: str = "meta-llama/Llama-3.2-3B-Instruct",
        embedding_model_name: str = "thenlper/gte-small",
        # rerank_model_name: str | None = "colbert-ir/colbertv2.0",
    ):
        self.vector_db = self._build_vector_db(model_name=embedding_model_name)
        self.llm = self._initialize_llm(model_name=llm_model_name)
        # if rerank_model_name is not None:
        #     self.reranker = RAGPretrainedModel.from_pretrained(rerank_model_name)
        # else:
        self.reranker = None

    def _initialize_llm(self, model_name):
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
        self.rag_prompt = tokenizer.apply_chat_template(PROMPT, tokenize=False, add_generation_prompt=True)

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
            knowledge_base: List[LangchainDocument],
            tokenizer_name: str
    ) -> List[LangchainDocument]:
        """
        Split documents into chunks of maximum size `chunk_size` tokens and return a list of documents.
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

        docs_processed = []
        logger.info(f"Processing docs in knowledge base...")
        for doc in knowledge_base:
            docs_processed += text_splitter.split_documents([doc])

        # Remove duplicates
        unique_texts = {}
        docs_processed_unique = []
        for doc in docs_processed:
            if doc.page_content not in unique_texts:
                unique_texts[doc.page_content] = True
                docs_processed_unique.append(doc)

        return docs_processed_unique

    def _build_vector_db(self, model_name):
        docs_processed = self.split_documents(chunk_size=512,
                             knowledge_base=RAW_KNOWLEDGE_BASE,
                             tokenizer_name=model_name)

        logger.info(f"Initializing embeddings {model_name=}")
        embedding_model = HuggingFaceEmbeddings(
            model_name=model_name,
            multi_process=True,
            model_kwargs={"device": "cuda"},
            encode_kwargs={"normalize_embeddings": True},  # Set `True` for cosine similarity
        )

        logger.info("Building vector store with FAISS...")
        return FAISS.from_documents(
            docs_processed, embedding_model, distance_strategy=DistanceStrategy.COSINE
        )

    def answer_with_rag(
        self,
        question: str,
        num_retrieved_docs: int = 30,
        num_docs_final: int = 5,
    ) -> tuple[str, List[LangchainDocument]]:
        # TODO add response from llm with identity - move chat template here?
        # Gather documents with retriever
        logger.info(" Retrieving documents...")
        relevant_docs = self.vector_db.similarity_search(query=question, k=num_retrieved_docs)
        relevant_docs = [doc.page_content for doc in relevant_docs]  # Keep only the text

        # Optionally rerank results
        if self.reranker:
            logger.info("Reranking documents...")
            relevant_docs = self.reranker.rerank(question, relevant_docs, k=num_docs_final)
            relevant_docs = [doc["content"] for doc in relevant_docs]

        relevant_docs = relevant_docs[:num_docs_final]

        # Build the final prompt
        context = "\nExtracted documents:\n"
        context += "".join([f"Document {str(i)}:::\n" + doc for i, doc in enumerate(relevant_docs)])

        final_prompt = self.rag_prompt.format(question=question, context=context)

        # Redact an answer
        logger.info("Generating answer...")
        answer = self.llm(final_prompt)[0]["generated_text"]

        return answer, relevant_docs

    # endregion
