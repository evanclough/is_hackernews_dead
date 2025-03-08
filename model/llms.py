class LLMError(Exception):
    def __init__(self, message):
        super().__init__(message)

def get_llm(llm_config):
    llms = {
        "openai 4o mini": OpenAILLM
    }

    if not ('name' in llm_config):
        raise LLMError(f"Error: LLM config dict missing name")

    if not (llm_config['name'] in llms):
        raise LLMError(f"Error: provided llm name {llm_config['name']} not in available LLM dict.")

    return llms[llm_config['name']](llm_config)

class LLM:
    def __init__(self, config):

        self.max_output_tokens = config['max_output_tokens']
        self.context_window = config['context_window']
        self.input_token_cost = config['input_token_cost']
        self.cached_input_token_cost = config['cached_input_token_cost']
        self.output_token_cost = config['output_token_cost']

        self.accrued_input_tokens = 0
        self.accrued_cached_input_tokens = 0
        self.accrued_output_tokens = 0

    def get_cost_estimate(self, prompt, cached_ratio=0.0, output_token_estimate=100, example_output=None):
        cost_estimate = 0
        prompt_tokens = self.tokenize(prompt)
        cost_estimate += cached_ratio * prompt_tokens * self.cached_input_token_cost
        cost_estimate += (1 - cached_ratio) * prompt_tokens * self.input_token_cost

        if example_output == None:
            cost_estimate += output_token_estimate * self.output_token_cost
        else:
            cost_estimate += self.tokenize(example_output) * self.output_token_cost

        return cost_estimate


    def get_accrued_cost(self):
        accrued_cost = 0

        accrued_cost += self.accrued_input_tokens * self.input_token_cost
        accrued_cost += self.accrued_cached_input_tokens * self.cached_input_token_cost
        accrued_cost += self.accrued_output_tokens * self.output_token_cost

        return accrued_cost



class OpenAILLM(LLM):
    def __init__(self, config):
        super().__init__(config)

        self.model_name = config['model_name']
        self.dev_prompt = config['dev_prompt']

        from openai import OpenAI
        self.client = OpenAI()

    def tokenize(self, prompt):
        encoding = tiktoken.encoding_for_model(model)
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




