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






