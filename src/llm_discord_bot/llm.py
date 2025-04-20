import torch
import transformers
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

logger = logging.getLogger("LLAMA")

class Llm:
    def __init__(self, model_path):
        self.model_id = model_path
        self.pipeline = transformers.pipeline(
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

    def get_response(
            self, query, message_history=[], max_tokens=4096, temperature=0.6, top_p=0.9
    ):
        # TODO deprecate?
        user_prompt = message_history + [{"role": "user", "content": query}]
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
        response = outputs[0]["generated_text"][len(prompt):]
        return response, user_prompt + [{"role": "assistant", "content": response}]


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

    def chatbot(self, system_instructions=""):
        conversation = [{"role": "system", "content": system_instructions}]
        while True:
            user_input = input("Prompt > ")
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting the chatbot. Goodbye!")
                break
            response, conversation = self.get_response(user_input, conversation)
            print(f"Assistant: {response}\n")


if __name__ == "__main__":
    # model = "meta-llama/Llama-3.2-3B-Instruct"
    model = "deepseek-ai/DeepSeek-V3-0324"
    bot = Llm(model)
    bot.chatbot()
