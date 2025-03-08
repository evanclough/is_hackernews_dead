from openai import OpenAI
from tiktoken import encoding_for_model

class LLMError(Exception):
    def __init__(self, message):
        super().__init__(message)

def get_llm(llm_config):
    llms = {
        "gpt-4o-mini": OpenAILLM
    }

    if not ('name' in llm_config):
        raise LLMError(f"Error: LLM config dict missing name")

    if not (llm_config['name'] in llms):
        raise LLMError(f"Error: provided llm name {llm_config['name']} not in available LLM dict.")

    return llms[llm_config['name']](llm_config)

class LLM:
    def __init__(self, config):

        self.name = config['name']
        self.max_output_tokens = config['max_output_tokens']
        self.context_window = config['context_window']
        self.input_token_cost = config['input_token_cost']
        self.cached_input_token_cost = config['cached_input_token_cost']
        self.output_token_cost = config['output_token_cost']

        self.accrued_input_tokens = 0
        self.accrued_cached_input_tokens = 0
        self.accrued_output_tokens = 0

    def estimate_prompt_cost(self, cached, uncached, output_token_estimate=100, example_output=None, accrue=False):
        cost_estimate = 0
        cached_tokens = self.tokenize(cached)
        input_tokens = self.tokenize(uncached)
        output_tokens = output_token_estimate if example_output == None else self.tokenize(example_output) 

        cost_estimate += cached_tokens * self.cached_input_token_cost
        cost_estimate += input_tokens * self.input_token_cost
        cost_estimate += output_tokens * self.output_token_cost

        if accrue:
            self.accrued_input_tokens += input_tokens
            self.accrued_cached_input_tokens += cached_tokens
            self.accrued_output_tokens += output_tokens

        return cost_estimate

    def __str__(self):
        return f"LLM {self.name}"

    def get_accrued_cost(self):
        accrued_cost = 0

        accrued_cost += self.accrued_input_tokens * self.input_token_cost
        accrued_cost += self.accrued_cached_input_tokens * self.cached_input_token_cost
        accrued_cost += self.accrued_output_tokens * self.output_token_cost

        return accrued_cost

    def print_accrued_costs(self):

        print(f"Current accrued costs for {self}:")
        print(f"{self.accrued_input_tokens} input tokens at rate ${self.input_token_cost}: {self.accrued_input_tokens * self.input_token_cost}")
        print(f"{self.accrued_cached_input_tokens} input tokens at rate ${self.cached_input_token_cost}: {self.accrued_cached_input_tokens * self.cached_input_token_cost}")
        print(f"{self.accrued_output_tokens} output tokens at rate ${self.output_token_cost}: {self.accrued_output_tokens * self.output_token_cost}")
        print(f"Total accrued cost: {self.get_accrued_cost()}")


class OpenAILLM(LLM):
    def __init__(self, config):
        super().__init__(config)

        self.model_name = config['model_name']
        self.dev_prompt = config['dev_prompt']

        self.client = OpenAI()

    def tokenize(self, prompt):
        encoding = encoding_for_model(self.model_name)
        tokens = encoding.encode(prompt)
        return len(tokens)

    def complete(self, prompt):
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "developer", "content": self.dev_prompt},
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        self.accrued_input_tokens += completion.usage.prompt_tokens
        self.accrued_output_tokens += completion.usage.completion_tokens

        return completion.choices[0].message.content




