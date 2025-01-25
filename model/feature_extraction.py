"""
    Various functions to extract additional features to add to the original datasets.
"""

from pydantic import BaseModel

import utils

"""
    Class for structuring the LLM's output for tasks which require it 
    to return a list of strings.
"""
class StringList(BaseModel):
    items: list[str]

"""
    for feature extraction errors 
"""
class FeatureExtractionError(Exception):
    def __init__(self, message):
        super().__init__(message)


"""
    Get a list of text samples for a given user that are particularly indicative
    of their grammar, to be used in generation.
"""
def get_text_samples(username, comment_history, num_samples, openai_client, skip_sub_ret_errors=False):
    print(f"Generating text samples for user {user_profile.username}...")

    prompt = f"""
            You will be given a selection of comments made by
            a user on an online forum. Extract a list of {num_samples} of these comments which are 
            most indicative of this user's particular grammar and dialect. This list should contain 
            only the comments themselves, with no additional commentary.

            Here are the comments:"""


    for comment in comment_history:
        prompt += "\n\nCOMMENT:\n"
        prompt += comment.text

    response = utils.get_gpt4o_structured_response(openai_client, prompt, StringList, print_usage=True, dev_prompt="You are to assist in a data extraction task. Do not include any markdown in your responses.")

    return response.items

"""
    Get a list of beliefs for a given user, as determined by LLM.
"""
def get_beliefs(username, submissions, num_beliefs, belief_char_max, openai_client, skip_sub_ret_errors=False):

    print(f"Generating beliefs for user {username}...")

    prompt = f"""
        You will be given information on a user on an online forum,
        including a selection of their past comments, a selection of their 
        past posts, and their favorited posts. With this, 
        create a list with length {num_beliefs} of concise paragraphs with a maximum length
        of {belief_char_max} characters, describing beliefs this user holds, 
        with these ordered from strongest to weakest, with first being strongest, and last being weakest.

        Here are some of the user's posts:"""
    for post in submissions["posts"]:
        prompt += "\n\nPOST:\n"
        prompt += post.get_featurex_str()

    prompt += "\nHere are some of the user's comments:\n"
    for comment in submissions["comments"]:
        prompt += "\n\nCOMMENT:\n"
        prompt += comment.text
    
    prompt += "\nHere are the user's favorited posts:\n"
    for favorite_post in submissions["favorite_posts"]:
        prompt += "\n\nFAVORITE POST:\n"
        prompt += favorite_post.get_featurex_str()

    response = utils.get_gpt4o_structured_response(openai_client, prompt, StringList, print_usage=True, dev_prompt="You are to assist in a data extraction task. Do not include any markdown in your responses.")

    return response

"""
    Get a list of interests for a given user, as determined by LLM.
"""
def get_interests(username, submissions, num_interests, openai_client, skip_sub_ret_errors=False):

    print(f"Generating interests for user {username}...")

    prompt = f"""
        You will be given information on a user on an online forum,
        including a numbered list of their past comments, a numbered list of their 
        past posts, and a numbered list of their favorited posts. With this, 
        create a list with length {num_interests} of different subjects the user is interested in
        with these ordered from strongest to weakest, with first being strongest, and last being weakest.

        Here are some of the user's posts:"""

    for post in submissions["posts"]:
        prompt += "\n\nPOST:\n"
        prompt += post.get_featurex_str()

    prompt += "\nHere are some of the user's comments:\n"
    for comment in submissions["comments"]:
        prompt += "\n\nCOMMENT:\n"
        prompt += comment.text
    
    prompt += "\nHere are the user's favorited posts:\n"
    for favorite_post in submissions["favorite_posts"]:
        prompt += "\n\nFAVORITE POST:\n"
        prompt += favorite_post.get_featurex_str()

    response = utils.get_gpt4o_structured_response(openai_client, prompt, StringList, print_usage=True, dev_prompt="You are to assist in a data extraction task. Do not include any markdown in your responses.")

    return response