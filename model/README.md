# Model

Python functionalities for creating and running the two models necessary for the experiment.

The way I interpret things, the task of creating a convincing bot can be split into two sub-problems:

 - *When* the bot posts
 - *What* the bot posts

Deciding when the bot posts is a simple yes or no question, a function with the bot's profile and the content string in question passed as input, and whether or not they respond as output.

Deciding what the bot posts is a bit more complicated, but thankfully large language models are powerful enough to do most of the work for us.

In reality, the bulk of the work (code) will be done on the *when* : I'll curate the input features to be as descriptive as possible, test out different models with different hyperparameters, and pick the one that produces the most convincing results.

The *what* problem sholud be solved by some simple RAG with the inputs described earlier, and a bit of prompt engineering.

## The *When* model

### Training and Testing
The model wlil be trained on real HN data gathered in the data module, with all feature data from users being a format I can create synthetically in making my bots.
The datasets are formatted as follows:
 - a list of "content strings", or potential items a given user could respond to
 - a list of user profiles.

The inference process for the model will consist of:
 - Taking an initial list of content strings, keeping all before some time T, and caching the rest to be added later.
 - Iterating through time on some given interval, starting at T, 
 - Iterate through each content string currently in the pool,
 - Iterate throguh each user currently in the pool,
 - Decide whether or not the user will respond to the content string
 - At the end of inference, add in all cached content strings posted during that time interval.