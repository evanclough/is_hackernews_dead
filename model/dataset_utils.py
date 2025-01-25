"""
    A script to with various functionalities for loading, modifying, and analyzing existing datasets.
    Janky af
"""

from dataset import Dataset
import utils
import sys

"""
    Create a new dataset from scratch.
"""
def _create_dataset(dataset_name):
    return Dataset(dataset_name)

"""
    Make a copy of a given dataset.
"""
def _copy_dataset(source_name, destination_name):
    utils.load_env()
    root_dataset_path = utils.fetch_env_var("ROOT_DATASET_PATH")
    source_path = root_dataset_path + source_name
    destination_path = root_dataset_path + destination_name
    utils.copy_directory(source_path, destination_path)

    print(f"Successfully copied dataset {source_name} to dataset {destination_name}.")

"""
    Slice a PRT in the dataset, given its root ID, and a starting and ending
    index of kids to include.
"""
def _slice_prt(dataset_name, root_id, start_index, end_index, update_profile, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(copy, existing_dataset_name=dataset_name)
    root = dataset.prf.get_item(int(root_id))
    kids = root.get_kids()
    kid_ids_to_remove = [kid.get_id() for i, kid in enumerate(kids) if i < int(start_index) or i >= int(end_index)]
    dataset.remove_comments(kid_ids_to_remove, update_author_profile=(update_profile == "YES"))

"""
    Slice the PRF of a given dataset by a starting and ending index.
"""
def _slice_prf(dataset_name, start_index, end_index, update_profile, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name)
    roots = dataset.prf.get_roots()
    root_ids_to_remove = [root.get_id() for i, root in enumerate(roots) if i < int(start_index) or i >= int(end_index)]
    dataset.remove_root_posts(root_ids_to_remove, update_author_profile=(update_profile == "YES"))

"""
    Add a list of new users to the user pool of a given dataset, 
    from a specified JSON containing raw attributes.
"""
def _add_users(dataset_name, user_json_path, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name)
    user_dicts = utils.read_json(user_json_path)
    dataset.add_users(user_dicts)

"""
    Remove a user from the dataset.
"""
def _remove_user(dataset_name, username, full, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name)
    dataset.remove_users([username], remove_posts=(full == "YES"), remove_comments=(full == "YES"))

"""
    Add a list of new posts to the PRF of a given dataset, 
    from a specified JSON containing raw attributes.
"""
def _add_posts(dataset_name, post_json_path, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name)
    post_dicts = utils.read_json(post_json_path)
    dataset.add_root_posts(post_dicts)

"""
    Add a list of new comments to the PRF of a given dataset, 
    from a specified JSON containing raw attributes.
"""
def _add_comments(dataset_name, comment_json_path, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name)
    comment_dicts = utils.read_json(comment_json_path)
    dataset.add_leaf_comments(comment_dicts)

"""
    Initialize a chroma db and generate embeddings for an existing dataset
    in the original format produced in the data module.
"""
def _embed_dataset(dataset_name, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name, init_chroma=True)

"""
    Print the full user pool of the dataset.
"""
def _print_user_pool(dataset_name):
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name)
    for username in dataset.user_pool.usernames:
        user_str = dataset.user_profile_str(username)
        print(user_str)

"""
    Print a given user's profile in the given dataset.
"""
def _print_user(dataset_name, username):
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name)
    user_str = dataset.user_profile_str(username)
    print(user_str)

"""
    Print an item in the given dataset.
"""
def _print_item(dataset_name, item_id):
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name)
    item_str = dataset.item_str(int(item_id))
    print(item_str)

"""
    Print the full branch of an item in the given dataset.
"""
def _print_branch(dataset_name, item_id):
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name)
    item_str = dataset.branch_str(int(item_id))
    print(item_str)

if __name__ == "__main__":
    func_map = {
        "create": _create_dataset,
        "copy": _copy_dataset,
        "slice_prt": _slice_prt,
        "slice_prf": _slice_prf,
        "add_users": _add_users,
        "add_posts": _add_posts,
        "remove_user": _remove_user,
        "add_comments": _add_comments,
        "embed": _embed_dataset,
        "print_user_pool": _print_user_pool,
        "print_user": _print_user,
        "print_item": _print_item,
        "print_branch": _print_branch
    }

    func_map[sys.argv[1]](*sys.argv[2:])
    

