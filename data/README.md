# Data

A collection of NodeJS scripts to form datasets for training and running the models from past Hacker News Data

## Current Usage

Datasets can be formed from either past Hacker News front pages, or the current top/best post endpoints

The process involves first scraping the raw data into a big JSON, then taking those big JSONs and placing them into a dataset, which contains a JSON list of usernames, for the uesr pool, a JSON containing IDs for all comment strings, and a sqlite database containing (ideally) all users, posts, and comments corresponding to those usernames and IDs.

To use past data, one must first retrieve the HTML for the desired past front page, with `getFrontPages.js`, then create the big json with `getPastData.js`. 

To use current data, one can use `getCurrentData.js`.

Then, once the big JSON has been made, one can create the final dataset `getCompletedDataset.js`. This is done in batches with separate `exec` calls for each, as when I tried to do it all at once the heap exploded.

To merge all of the batches produced by the prior script, one can use `mergeBatchedCompleteDataset.js`.