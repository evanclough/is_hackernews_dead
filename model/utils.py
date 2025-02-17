"""
    Various utility functions to be used throughout the module.
"""
import os
import json
import pathlib
import shutil
import tiktoken


from dotenv import load_dotenv

def fetch_env_var(name):
    load_dotenv()
    env_var = os.getenv(name)
    if env_var == None:
        raise ValueError(f"Error fetching environment variable {name}: it does not exist")
    else:
        return env_var

def read_json(json_path):
    with open(json_path, 'r') as file:
        json_data = json.load(file)
    print(f"Successfully read from {json_path}")
    return json_data

def write_json(json_data, json_path):
    with open(json_path, 'w') as file:
        json.dump(json_data, file, indent=4)
    print(f"Successfully wrote to {json_path}.")

def create_directory(path):
    directory = pathlib.Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    os.makedirs(directory, exist_ok=True)

def check_directory_exists(path):
    directory_path = pathlib.Path(path)
    return directory_path.is_dir()

def copy_directory(source, destination):
    shutil.copytree(source, destination)

def remove_directory(path):
    shutil.rmtree(path)

def get_dataset_path(dataset_name):
    root_dataset_path = fetch_env_var("ROOT_DATASET_PATH")
    return root_dataset_path + dataset_name



"""
    Get a response from a specified openai model.
"""
def get_openai_response(openai_client, model, prompt, print_usage=False, dev_prompt=None):
    messages = []
    if dev_prompt != None:
        messages.append({"role": "developer", "content": dev_prompt})
    messages.append({"role": "user", "content": prompt})

    completion = openai_client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=response_format,
    )

    response = completion.choices[0].message.content

    if print_usage:
        print(f"Token usage for prompt {prompt[:100]} on model {model}:")
        print(f"Prompt tokens: {completion.usage.prompt_tokens}")
        print(f"Completion tokens: {completion.usage.completion_tokens}")
        print(f"Total tokens: {completion.usage.total_tokens}")

    return response

"""
    Get the number of input tokens for a given openai prompt, with a given model.
"""
def get_openai_token_estimate(prompt, model):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(prompt)
    return len(tokens)

"""
    Get a structured response from gpt4o, given a list of messages, and a response format class.
"""
def get_gpt4o_structured_response(openai_client, prompt, response_format, print_usage=False, dev_prompt=None):

    messages = []
    if dev_prompt != None:
        messages.append({"role": "developer", "content": dev_prompt})
    messages.append({"role": "user", "content": prompt})

    completion = openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=messages,
        response_format=response_format,
    )

    response = completion.choices[0].message.parsed

    if print_usage:
        print(f"Token usage for prompt {prompt[:100]} on model gpt-4o:")
        print(f"Prompt tokens: {completion.usage.prompt_tokens}")
        print(f"Completion tokens: {completion.usage.completion_tokens}")
        print(f"Total tokens: {completion.usage.total_tokens}")

    return response