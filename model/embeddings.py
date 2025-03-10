from tiktoken import encoding_for_model
import chromadb

import utils

class EmbeddingModelError(Exception):
    def __init__(self, message):
        super().__init__(message)

def get_embedding_model(embedding_config):
    models = {
        "openai": OpenAIEmbeddingModel
    }

    if not ('name' in embedding_config):
        raise EmbeddingModelError(f"Error: embedding model config dict missing name")

    if not (embedding_config['name'] in models):
        raise EmbeddingModelError(f"Error: provided embedding model name {embedding_config['name']} not in available embedding models dict.")

    return models[embedding_config['name']](embedding_config)

class EmbeddingModel:
    def __init__(self, config):
        self.name = config['name']
        self.max_tokens = config["max_tokens"]
        self.input_token_cost = config["input_token_cost"]
        self.dimension = config['dimension']

        self.accrued_input_tokens = 0

    def estimate_doc_cost(self, doc, accrue=False):
        cost_estimate = 0
        input_tokens = self.tokenize(doc)
        cost_estimate += input_tokens * self.input_token_cost

        if accrue:
            self.accrued_input_tokens += input_tokens

        return cost_estimate

    def __str__(self):
        return f"Embedding Model {self.name}"

    def get_accrued_cost(self):
        accrued_cost = 0

        accrued_cost += self.accrued_input_tokens * self.input_token_cost

        return accrued_cost

    def print_accrued_costs(self):

        print(f"Current accrued costs for {self}:")
        print(f"{self.accrued_input_tokens} input tokens at rate ${self.input_token_cost}: {self.accrued_input_tokens * self.input_token_cost}")
        print(f"Total accrued cost: {self.get_accrued_cost()}")


class OpenAIEmbeddingModel(EmbeddingModel):
    def __init__(self, config):
        super().__init__(config)

        self.model_name = config['model_name']

    def get_chroma_embedding_function(self):
        return chromadb.utils.embedding_functions.OpenAIEmbeddingFunction(
            api_key=utils.fetch_env_var("OPENAI_API_KEY"),
            model_name=self.model_name
        )

    def tokenize(self, document):
        encoding = encoding_for_model(self.model_name)
        tokens = encoding.encode(document)
        return len(tokens)
        

