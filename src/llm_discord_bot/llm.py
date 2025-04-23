import torch
import logging
from transformers import pipeline

logger = logging.getLogger("LLM")

class Llm:
    def __init__(self, model_path):
        self.model_id = model_path
        self.pipeline = pipeline(
            task="text-generation",
            model=self.model_id,
            model_kwargs={
                "torch_dtype": torch.bfloat16
            },
            device='cuda:0'
        )
        self.terminators = [
            self.pipeline.tokenizer.eos_token_id,
            self.pipeline.tokenizer.convert_tokens_to_ids("<|eot_id|>"),
        ]

    def response(self, query, identity, max_tokens=4096, temperature=0.6, top_p=0.9):
        user_prompt = [{"role": "system", "content": identity}, {"role": "user", "content": query}]
        prompt = self.pipeline.tokenizer.apply_chat_template(
            user_prompt, tokenize=False, add_generation_prompt=True
        )
        outputs = self.pipeline(
            prompt,
            max_new_tokens=max_tokens,
            eos_token_id=self.terminators,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
        )
        return outputs[0]["generated_text"][len(prompt):]
