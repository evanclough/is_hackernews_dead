"""
    Various utility functions to be used throughout the module.
"""
import os
import json

from dotenv import load_dotenv

def fetch_env_var(name):
    load_dotenv()
    return os.getenv(name)

def read_json(json_path):
    with open(json_path, 'r') as file:
        json_data = json.load(file)
    print(f"Successfully read from {json_path}")
    return json_data

def write_json(json_data, json_path):
    with open(json_path, 'w') as file:
        json.dump(json_data, file, indent=4)
    print(f"Successfully wrote to {json_path}.")
