# Data

A collection of functions which make use of the Hacker News API to gather and prepare the data necessary for the experiment.

Per the [API](https://github.com/HackerNews/API), there are 5 types for "items", or user posted content. 
Story, which is a link post, Ask, which is a post with a body, Comment, Job, which is just a link to a job posted on ycombinator, and Poll.
To keep things simple, to start, we'll only worry about Stories, Comments, and Ask posts.
These can all be fetched with the same endpoint, with varying IDs: https://hacker-news.firebaseio.com/v0/item/<id>.json(?print=pretty)
Here are the schemas for the three types:
    - story: {
        "by" : "dhouston",
        "descendants" : 71,
        "id" : 8863,
        "kids" : [ 8952, 9224, 8917, 8884, 8887, 8943, 8869, 8958, 9005, 9671, 8940, 9067, 8908, 9055, 8865, 8881, 8872, 8873, 8955, 10403, 8903, 8928, 9125, 8998, 8901, 8902, 8907, 8894, 8878, 8870, 8980, 8934, 8876 ],
        "score" : 111,
        "time" : 1175714200,
        "title" : "My YC app: Dropbox - Throw away your USB drive",
        "type" : "story",
        "url" : "http://www.getdropbox.com/u/2/screencast.html"
    }
    - comment: {
        "by" : "norvig",
        "id" : 2921983,
        "kids" : [ 2922097, 2922429, 2924562, 2922709, 2922573, 2922140, 2922141 ],
        "parent" : 2921506,
        "text" : "Aw shucks, guys ... you make me blush with your compliments.<p>Tell you what, Ill make a deal: I'll keep writing if you keep reading. K?",
        "time" : 1314211127,
        "type" : "comment"
    }
    - ask: {
        "by" : "tel",
        "descendants" : 16,
        "id" : 121003,
        "kids" : [ 121016, 121109, 121168 ],
        "score" : 25,
        "text" : "<i>or</i> HN: the Next Iteration<p>I get the impression that with Arc being released a lot of people who never had time for HN before are suddenly dropping in more often. (PG: what are the numbers on this? I'm envisioning a spike.)<p>Not to say that isn't great, but I'm wary of Diggification. Between links comparing programming to sex and a flurry of gratuitous, ostentatious  adjectives in the headlines it's a bit concerning.<p>80% of the stuff that makes the front page is still pretty awesome, but what's in place to keep the signal/noise ratio high? Does the HN model still work as the community scales? What's in store for (++ HN)?",
        "time" : 1203647620,
        "title" : "Ask HN: The Arc Effect",
        "type" : "story"
    }

Fetching users can be done at the endpoint: https://hacker-news.firebaseio.com/v0/user/<username>.json(?print=pretty)
Here's the schema: 
    - user: {
        "about" : "This is a test",
        "created" : 1173923446,
        "id" : "jl",
        "karma" : 2937,
        "submitted" : [ 8265435, ... ]
    }

There are also endpoints to fetch the current top, best, and new stories (unsure what the difference is between top and best), at https://hacker-news.firebaseio.com/v0/(top|best|new)stories.json(?print=pretty).
You can also use these for Ask, Job Job posts
The schema is just an array of IDs.


This is all the access that is provided, which is a bit unfortunate, as ideally I'd be able to directly fetch a popular page for a given timestamp.

However, I can still do this rather easily, hopefully without causing trouble, by scraping https://news.ycombinator.com/front?day=<year>-<month>-<day>.

I shouldn't need too many of these, if the scraper runs into a problem I could do it manually, as all of the data I need from them will be retrieved using real endpoints


Progress 1/1: Have secured list of post IDs for 5 years worth of front pages
1/4: the scraper for past front pages is done, code isn't great but it'll do, everything i need 
is being retrieved. Need to migrate the data to a format that can be used for eventual training/testing.
Would be easiest to work with in a standard relational format, table for posts, table for comments, table for users, table for link content.
Going to use a ?

Need to take the raw data and create formal datasets for a given date range that can be used for training/testing.

The formal problem is: 

Given a string of content, consisting of a post, and n comments, will this user respond?

So, the two overarching features are the user, and the content string.

Need to take the raw parsed data, and convert to a format which fits this problem.

Users can be fixed, to start. I'll come up with a feature set for them.

The task is to create a front page.
How will I do this?

Start with a base list of content strings, which is just posts at first.
Then, every n seconds,
    for each content string in the front page,
        for each user,
            Will they respond?
            if so, add this to the list of posts.

so, to do a training run of the model, I will need:
A pool of users, with various features.
A list of content strings.

Right now, I have:
posts: [
    post: {
        contents: abc
        comments: [{ contents: abc}, [{contents: def}], {contents: abc}]
    }
]

it would be easier to work with comments as a json, with child comments contained within.
other than that, the format is fine.

1/5
The scraper is almost done.

Next tasks:
Feature Extraction from link content
Feature Extraction from users

Desire:
Inject posts from fake users into the Hacker News front page, and see if they're distinguishable from those of real users.

What Do I Need?
First, a front page to inject the data into.

This could potentially be a current front page, maybe an hour behind, with bot posts injected and usernames hidden.
Would be much more difficult.

So, at first, I'll work with past front pages. 

Given some past front page, which is a list of content strings FP, or [C], on some given day D:


Some proportion of the content strings will be removed entirely.

Given some starting time T0, after which all posts have been made...
or, it doesn't necessarily matter, to start i could just have the preset list of posts...

all content strings beginning afterwards will be cached to be inserted later.

After that time T0, periodically, at some interval with length I, at every following time Ti

first, all original content strings will be binned into these times and re-inserted when the time comes.

for each bot in a list [B],
for each potential content string C from FP, which is a post, followed by 0 or more comments,
I will run the bots corresponding model, to determine whether or not the bot will respond to C at that time.
If it determines yes, I will use an LLM, with RAG from the bots various attributes, 
to generate the bots response, and add it to the content string list accordingly.

To enhance deception, bots will be split into two categories:

True bots, with no starting post history, with characteristics entirely predetermined.

and, 

Person bots, who will start with the same post history as an existing user,
with all of that person's characteristics.

So, usernames on the front-end will be hidden, and the game will be to place the author of each comment
into one of the three categories.

model: will_person_post(features) -> yes or no

features:

can be put into a few categories:
deterministic user
deterministic content string
deterministic (user, content string)
BERT (content string)
bert (user)...

1/8

Timeline: Get the frontend and corresponding article released by the end of the month.

Current Status: I have the raw data for content strings for a given timeframe,
and all users who've posted in them.

The process for training the model is stated above. 

Tasks:

Initial Iteration (January):

- Finalize dataset structure.

    - Create process for feature extraction for users in pool.
        - Come up with schema for final user objects
        - Migrate entries in user pool array to list of final user objects.

    - Create process for feature extraction for each given content string.
        - Come upw ith schema for final content string objects.
            - Standardize post contents for both link and text body posts.
        - Migrate entries in posts array to list of final content string objects.

    - Create process for feature extraction for combined user/content string features
        - Come up with schema
        - A function to be run prior to each inference run of the When To Post model

- Determine way to run model
     - See if running is feasible on local machine
        - if not, evaluate both AWS and CSH servers as options.

- Create testing system for different models
    - Create initial visualization for output
         - Not sure if would be quicker to just do the frontend
    - Create schema to result metrics

- Create frontend for displaying results, for a static run.
- Clean code for publishing.
- Write article summarizing results.

Future Ideas:
- Create live port that runs T time behind the real Hacker News
- Create human feedback mechanism to be run with the live port


User Feature Extraction:
First, users should be in a database, so retrieving them during training is faster than searching the json, and also for RAG.
Post history and other text stuff can be embedded for RAG during generation time.

But to start the schema:

What I have from HN:
 - user: {
        "about" : "This is a test",
        "created" : 1173923446,
        "id" : "jl",
        "karma" : 2937,
        "submitted" : [ 8265435, ... ]
    }

Can do immediately: fetch items in submitted list

Probably don't need entire post history of necessary, could take that at basis

The schema needs to consist of things that I can replicate from scratch in creating a bot.

These profiles will be created initially for a given user pool, but could be updated over time.

Would be good to keep it minimal to start:

user {
    public facing:
        {
            id: username,
            karma,
            created,
            about?,
            submitted,
        }
    private:
        {
            post_frequency,
            comment_frequency,
            text_samples:   a few sentences as an example for the user's grammar/cadence, 
                            to be passed into LLM call for generation,
            interests:      A list of strings on topics the user is interested in, ranked.
                            LLM Prompt: "Given this user's post history, please give their top five topics of interest, in JSON format, as a list of strings.
            beliefs:        A list of strings of beliefs the user has, ranked.
        }

}

LLM:
Gonna start with OpenAI, but swapping it out / testing others in the long run would be trivial

GPT-4o pricing:
$0.00250 / 1K input tokens

1/10: 

The LLM shit should be done in python.

Create a database, finish the scraping pipeline to do all non-LLM work in javascript, 
put all in database, then LLM shit in python, then we ready

users table, posts table, comments table,
user pools can be left as usernames, used to pull from database in running the model.
content strings will be converted to a list of IDs to pull from database

when im ready:
make users table
finish js pipeline to put all user shit in there
make posts/comments table
finish js pipeline to put all post/comment shit in there
write python pipelines to use LLMs for final feature extraction from user pools and content string list into database
run the model!

1/16:

finally time to get the llm involved

hopefully done with the data module, code isn't great but it works
and im tired of writing javascript

python intake of the sqlite datasets is fine. 
will need to add a few columns.

next steps:

get LLM involved in python to generate necessary features with that
populate in sqlite -> make embeddings
figure out embedding storage, should be pretty easy with the way i have things set up now,
just add to chroma in some easily accessible way

then write function to add a new comment to the dataset during a run once thats figured out

write function to finally make the initial feature set for each user/potential response

(come up with a better naming scheme for the things people can potentially respond to!)
(and for the dataset shit eventually too its a mess rn)

try out different models for when

make rag system for generation / prompt engineering for what model and evaluate those results, will be fun
make an evaluation system for response quality for testing.

do a test run to evaluate results

make frontend


1/21:
it was not in fact time to get the LLM involved.
however now it may be.
the dataset class works, now finally get to do some feature extraction from the original data
the things i can think of immediately would be:

curating the link content for posts. there aren't many of them, it could be done manually,
but would also be cool to have LLM summarization as an option.

filling in the user profile fields i created all that time ago

that's about it for initial stuff...

once i have a pipeline for doing that, 
(and get a real complete dataset...)
then generate embeddings and store
and actually train.

1/29 TODO:
-remove nonexistant submissions from user history id lists
-get rid of disallowed tokens
-finish embedding token estimate
-abstract feature extraction / clean code
-switch to cheaper model for feature extraction
-pseudocode for when/where models and do a test run of generation
-make when model / training framework
-do rag for what to post
-run it! 

2/10:

we r back
todo:

abstract feature extraction:

provide functionality to arbitrarily add a column to any of the three datatypes.
first: add a json to the dataset, "features.json".
this will hold an array of entries with information on each custom feature

{
    item_type, 
    name,
    prompt, (templating)
    sqlite_type,
    py_type
}

insert in scraping?
no, is not necessary
on load: check if file is present, if so set flag, modify load accordingly
write function in dataset to add.
could just read in from sqlite?
no, want the prompt present to regenerate on command
STATUS 2/17: insertion works, selection/retrieval via classes needs to be done now. sqlite_db refactor is almost complete.


camelcase -> snake case col/table names (in js too)
(userProfiles -> users)

2/18: abstraction of sqlite_db is done, columns/tables have been properly renamed.
next, abstract the three item types 
2/21: done
(fix name schemes for shit)


2/22: 
convert item_type class to item_factory, one per dataset.
datatype -> item type name scheme
fix chroma 
sqlite/chroma/item_factory all initialized given att/feature lists.
function to update att/feature lists for all.

abstract beyond HN?
could be optimal. 
users, roots, comments, distinct structs for all instnaces of problem
this won't really come into play until training / inference / generation.

for abstraction, what do you need to create a dataset?

assuming for all instances of this problem, there are three primary entities:
users, 
roots, (items upon which response trees rest, posts, ?)
branches

so, with sqlite as the basis,
 - a python class for each
 - a sqlite table for each
 - a list of base attributes for each, 
 - a list of LLM-generated features for each
 - a name of the dataset, from which its directory location can be found (with env var)

all of these can be assessed, given the location of the dataset directory.
if nothing exists, create empty sqlite and chroma with designated attributes/features
provide option to create chroma database, if not present
provide option to embed existing text data, if not done
provide option to generate features

condense this for each dataset into an entities json: 

"users/roots/branches": {
    "sqlite_table_name",
    "base_attributes",
    "features",
}
base constructor: name, python classes for entities,  info dict, 

dataset state:
has embeddings
has LLM-generated features.
chroma database should be created for all upon init.

create from scratch:
create directory, create sqlite, create chroma.

create from existing directory (requires info dict): 
check if chroma exists, if not, create them.


TODO:
create json for entity info
item types -> entities
create item factory with entity classes

this is a big one
full refactor
chroma, sqlite, user pool (tentatively) is done
todo:
prf
item types -> entities
polymorphism: entity -> user/root/branch -> HN specific classes
keep going through dataset file
fix tests
test


2/26:
made a bit of a mess but refactor shall be done
abstract classes for users/roots/branches:


users abstract methods:
load sbumission history


submission abstract methods:
load author

how?
add loaded attributes section to entities json


todo:
conversions
fix chroma with is_list
identifier -> id_att, id_val
fix the name shit now

TEST ARRAY FLATTEN
test get_submission in ST
get flattened descendants -> convert to list
abstract verbose/_print

the clean method is now done with kwargs, optional checking on provided sources
PRF -> submission forest

get submission path??? come up with beter name

then, abstact add_feature function

2/28:
tasks:
finish up entity classes
parent will not be included in SF json.
how to do clean
should submission tree nodes be able to delete themselves?
users/roots/branches -> user/root/branch
derived attributes may be embedded!

change how embeddings are generated: abstract method for entities to return dict of all embedded atts


fixing names with SF
come up wiht new name for loaded attributes -> derived
what makes them loaded? they're not stored in sqlite
base attributes: 
come from a sqlite row.
derived attributes:
attributes that may be derived from the sqlite tables and base attributes.
may be embedded
generated attributes: 
generated from base and derived attributes via an LLM
or potentially any other source.
once generated, they *are* stored in sqlite/embedded.

2/28:
we're getting somewhere
dataset crud functions will be redone tomorrow
will fix tests and test the init/embedding generation for now.

there is a problem with the way the info dict is held in the entities classes
fix

has been fixed



3/1 tasks:
user/submission/branch/root abstract classes
fix entities info dict, pass through parameters
=====
so
to instantiate the custom entity classes, custom kwargs will be needed, for at least loading derived attributes.
just allow them to be passed into any dataset method which requires instantiation!
that works
now itd be much clearner to be able to load from sources with a simple array, rather than providign the database object every time.
this could be done through the up/sf objects
they can have their own copies of the DB objects
===

its coming along...
things are scuffed and hacky but they work
chroma issue: tables are being created via sqlite names but accessed via entity types

chroma needs to be cleaned up
then entity methods for adding to sqlite, generating, etc, are trivial, 
will do in same way i did embeddings, kwargs dicts passed through dataset methods.

3/2: need new name for entities info dict. 
entity models?
thatll do
it should probably be an object, along with most of these scuffed dicts ive come to use as parameters for everything

dataset loaders:
dataset method: populate loader, adds sqlite/chroma/other shit if needed
loader object

derived attributes:
don't necessarily need to be from sqlite and chroma? just need to be from base attributes.
other parameters are arbitrary

loading an entity:
may load any attribute class: base, derived, or generated.
for base, may load from a dict or sqlite
for derived, may load with arbitrary load object for concrete class
for generated, may load from a dict or sqlite
may load embeddings for any class.
may generate embeddings for any class.

add/remove entities
generate features
filter content

3/3:
dataset:
has a sqlite table, a SF json with the trees, has a user pool as a list of uids.
entities: user, root, branch
each entity has attributes which may belong in three classes
base:
may be either directly loaded in as a row from the entities sqlite table,
or instantiated from an attribute dict.

baseloader: (source: sqlite | dict)

derived:
these are attributes derived from the datasets sqlite data and the base attributes.
the method to populate them is abstracted to the entity implementations.
sqlite is required. 
an optional object specific to the entity implementation may be passed as well.

derivedloader: (sqlite, custom_loader=None)

generated:
these are attributes generated by a speciifed prompt, and the base and derived attributes.
before they are generated, they are stored as empty in sqlite.
after generated, they are stored in sqlite. may also be populated as a dict.

generatedloader: (source: sqlite | dict)

AttClassLoader(load_embeddings: False)


this shit is breaking my brain
dataset:
created with an entity models json, with information on how to create each entity.
the entity class is initialized with this.
the entity classes then initializes its three attribute classes with the necessary information
the entity class must provide a method to return an object representing that entity.

entity factory:
initialized with dataset, has table name, id attribute.


entity_factory.get_dict(id, entity loader):
load designated attributes.
return dict with those attributes.

entity loader:
loader for base attributes, loader for derived attributes, loader for generated attributes.
joins them together, returns

all loaders:
may be custom
return dict of atts

when instantiating an entity, the only input that needs to be supplied is an id, and what to load.

entity:
base/derived/generated attribute classes
load_all: load on each
embed_all: embed on each



attribute class:
list of attribute models
load()
embed()
get_att


attribute model:
embed (or no)




clean scraping pipeline
add filtering
modularize all llm specific shit
write code for training/generation with abstract where/when models
make nice tui for doing shit
make frontend easy to run locally
c