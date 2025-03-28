"""
    A script to with various functionalities for loading, modifying, and analyzing existing datasets.
    Janky af
"""

from dataset import Dataset
import utils
import sys
import functools


"""
    Create a new dataset from scratch.
"""
def _create_dataset(dataset_name):
    return Dataset(dataset_name)

"""
    Create a testing dataset from preset data jsons.
"""
def _create_basic_test_dataset(dataset_name):
    dataset = Dataset(dataset_name)
    _add_users(dataset_name, "test_users.json", "NO")
    _add_posts(dataset_name, "test_posts.json", "NO")
    _add_comments(dataset_name, "test_comments.json", "NO")

"""
    Create a testing dataset from preset data jsons, with supposedly real users..
"""
def _create_real_test_dataset(dataset_name):
    dataset = Dataset(dataset_name)
    _add_users(dataset_name, "test_real_users.json", "NO")
    _add_posts(dataset_name, "test_real_posts.json", "NO")
    _add_comments(dataset_name, "test_real_comments.json", "NO")

"""
    Remove a given dataset.
"""
def _remove_dataset(dataset_name):
    dataset_path = utils.get_dataset_path(dataset_name)
    utils.remove_directory(dataset_path)
    print(f"Successfully removed dataset {dataset_name}")

"""
    Make a copy of a given dataset.
"""
def _copy_dataset(source_name, destination_name):
    source_path = utils.get_dataset_path(source_name)
    destination_path = utils.get_dataset_path(destination_name)
    utils.copy_directory(source_path, destination_path)

    print(f"Successfully copied dataset {source_name} to dataset {destination_name}.")

"""
    Slice a PRT in the dataset, given its root ID, and a starting and ending
    index of kids to include.
"""
def _slice_prt(dataset_name, root_id, start_index, end_index, update_profile, remove_users, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(copy, existing_dataset_name=dataset_name)
    root = dataset.prf.get_item(int(root_id))
    all_items_in_root = root.get_flattened_descendants()
    all_usernames_in_root = [item.fetch_contents(sqlite_db=dataset.sqlite_db).by for item in all_items_in_root]

    kids = root.get_kids()
    kid_ids_to_remove = [kid.get_id() for i, kid in enumerate(kids) if i < int(start_index) or i >= int(end_index)]
    dataset.remove_comments(kid_ids_to_remove, update_author_profile=(update_profile == "YES"))

    if remove_users == "YES":
        kept_kids = [kid for i, kid in enumerate(kids) if i >= int(start_index) and i < int(end_index)]
        all_items_in_kept_kids = functools.reduce(lambda acc, i: [*acc, *i], [kid.get_flattened_descendants() for kid in kept_kids], [root])
        all_usernames_in_kept_kids = [item.fetch_contents(sqlite_db=dataset.sqlite_db).by for item in all_items_in_kept_kids]
        
        usernames_to_remove = [username for username in all_usernames_in_root if not (username in all_usernames_in_kept_kids)]

        dataset.remove_users(usernames_to_remove, remove_posts=True, remove_comments=True)

"""
    Slice the PRF of a given dataset by a starting and ending index.
    Remove all users not present in the prf.
"""
def _slice_prf(dataset_name, start_index, end_index, update_profile, remove_users, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name)
    roots = dataset.prf.get_roots()
    root_ids_to_remove = [root.get_id() for i, root in enumerate(roots) if i < int(start_index) or i >= int(end_index)]
    dataset.remove_root_posts(root_ids_to_remove, update_author_profile=(update_profile == "YES"))
    if remove_users == "YES":
        kept_roots = [root for i, root in enumerate(roots) if i >= int(start_index) and i < int(end_index)]
        all_items_in_kept_roots = functools.reduce(lambda acc, r: [*acc, *r], [root.get_flattened_descendants() for root in kept_roots], [])
        all_usernames_in_kept_roots = [item.fetch_contents(sqlite_db=dataset.sqlite_db).by for item in all_items_in_kept_roots]
        
        all_usernames = dataset.user_pool.get_usernames()
        usernames_to_remove = [username for username in all_usernames if not (username in all_usernames_in_kept_roots)]

        dataset.remove_users(usernames_to_remove, remove_posts=True, remove_comments=True)


"""
    Add a list of new users to the user pool of a given dataset, 
    from a specified JSON containing raw attributes.
"""
def _add_users(dataset_name, user_json_path, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name)
    user_dicts = utils.read_json("./test_json/" + user_json_path)
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
    post_dicts = utils.read_json("./test_json/" + post_json_path)
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
    comment_dicts = utils.read_json("./test_json/" + comment_json_path)
    dataset.add_leaf_comments(comment_dicts)

"""
    Initialize a chroma db and generate embeddings for an existing dataset
    in the original format produced in the data module.
"""
def _embed_dataset(dataset_name, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name)
    print(dataset.has_chroma)

"""
    Run feature extraction on a given user.
"""
def _featurex_user(dataset_name, username, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name, use_openai_client=True)
    dataset.featurex_user(username)

"""
    Run feature extraction on all real users in a given dataset's user pool.
"""
def _featurex_user_pool(dataset_name, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name, use_openai_client=True)
    dataset.featurex_user_pool()

"""
    Summarize a postin the dataset's url content, given its id.
"""
def _summarize_post_url_content(dataset_name, post_id, copy):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name, use_openai_client=True)
    post_item = dataset.prf.get_item(post_id)
    post_contents = post_item.fetch_contents(sqlite_db=dataset.sqlite_db)
    post_dict = post_contents.get_sqlite_att_dict()
    dataset.summarize_url_content()

"""
    Summarize the URL content of all posts int he dataset.
"""
def _summarize_all_posts(dataset_name):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name, use_openai_client=True)
    dataset.summarize_all_posts()

def _full_featurex(dataset_name):
    if copy != "NO":
        _copy_dataset(dataset_name, copy)
        dataset_name = copy
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name, use_openai_client=True)
    dataset.full_featurex()

"""
    Get a cost estimate of full feature extraction on a dataset.
"""
def _featurex_cost_estimate(dataset_name):
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name, use_openai_client=True)
    dataset.full_openai_featurex_cost_estimate()

"""
    Get a cost estimate of generating embeddings for a dataset.
"""
def _embeddings_cost_estimate(dataset_name):
    dataset = Dataset(dataset_name, existing_dataset_name=dataset_name)
    dataset.ce_embedding_dataset()

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

"""
    Reset the test dataset to the stored copy.
"""
def _reset_test_dataset():
    test_dataset_name = utils.fetch_env_var("TEST_DATASET_NAME")
    test_dataset_path = utils.get_dataset_path(test_dataset_name)
    if utils.check_directory_exists(test_dataset_path):
        _remove_dataset(test_dataset_name)
    _copy_dataset(test_dataset_name + "_COPY", test_dataset_name)

if __name__ == "__main__":
    func_map = {
        "create": _create_dataset,
        "create_basic_test": _create_basic_test_dataset,
        "create_real_test": _create_real_test_dataset,
        "copy": _copy_dataset,
        "remove": _remove_dataset,
        "slice_prt": _slice_prt,
        "slice_prf": _slice_prf,
        "add_users": _add_users,
        "add_posts": _add_posts,
        "remove_user": _remove_user,
        "add_comments": _add_comments,
        "embed": _embed_dataset,
        "featurex_user": _featurex_user,
        "featurex_user_pool": _featurex_user_pool,
        "featurex_post": _summarize_post_url_content,
        "featurex_all_posts": _summarize_all_posts,
        "featurex_dataset": _full_featurex,
        "featurex_cost_estimate": _featurex_cost_estimate,
        "embeddings_cost_estimate": _embeddings_cost_estimate,
        "print_user_pool": _print_user_pool,
        "print_user": _print_user,
        "print_item": _print_item,
        "print_branch": _print_branch,
        "reset_tests": _reset_test_dataset,

    }

    func_map[sys.argv[1]](*sys.argv[2:])
    

