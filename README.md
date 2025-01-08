# Hacker News is Dead

An experiment to determine the power current large language models have in controlling discussion on popular technology forum, Hacker News.

The project will be a web-application.

Viewers of the web application will be able to select one of a number
of different Hacker News daily pages, from different past timestamps.

Each page will be generated with:
 - a list of post titles and topics, taken directly from the real Hacker News daily page at that timestamp
 - a set of real users, with real user names, and real post/comment historys, up until that timestamp
 - a set of LLM-generated users, with LLM-generated user-names, and LLM-generated post/comment historys.

A page will consist of a list of these posts, along with a timestamp.

Thereofre, the generation of a page will simply generate a list of posts

Each post will be generated with:
 - the list of comments from real users on that post
 - the set of LLM-generated users
 - the contents of the associated link or post body.

A post will consist of a list of comments, some of which are real, and some of which are fake.

Eahc fake comment will be generated with:
 - the contents of the post
 - the fake user's posting history
 - the contents of the parent comment, if present.

A fake comment will consist of a text body, along with an upvote score.

Fake users will be generated recursively.
To start, a username will be generated, based off of popular usernames at the time of the fake accounts creation.
Additionally, a "seed" will be used in creating the user: A paragraph, fed to the LLM, describing the user's opinions.
Given that seed, for each timestamp generated after the user's creation, their post history will subsequently be generated.

In pseudo JSON:

page:
 - timestamp: the timestamp for the page
 - is_real
 - posts: the real posts from the hackernews popular page for that timestamp
 - real_world_context: some form of real world context from that timestamp, not sure what yet

post: 
 - timestamp: the timestamp for the post
 - title
 - link (if present)
 - body (if present)
 - author
 - comments

comment: 
 - timestmap
 - body
 - author
 - points
 - parent comment

user: 
 - username
 - account creation timestamp
 - post history
 - comment history
 - seed: summary of user's beliefs. for real user, will be generated by llm. for fake user, will be provided upon creation

FUNCTIONS TO WRITE (IN ORDER):

get_real_page (timestamp)
fetches the real hacker news page for that given timestamp
fetches real world context for that given timestamp
for each post in the real page, gets info on that post

get_real_post (post_link)
fetches the title of the post
fetches the body of the post, if present
fetches the contents of the link of the post, if present (this may be difficult. at first, just generate an empty text file, containing the link, which can be filled manually).
fetches all comments of the post
fetches the user of the author of the post, along with all commenters

get_real_user (user_link)
fetches the username, and all available account info
fetches comment history
generates seed with this info (LLM)

create_fake_user (timestamp, seed)
creates a fake username/other user info at the given timestamp, with the given seed.

generate_fake_page(real_page, real_users, fake_users)
creates a fake page, consisting of a list of fake posts, with at first the same post body/links, but eventually, maybe also fake links/post bodies, given the real world context

generate_fake_link_post (real_link_post, real_users, fake_users):
simpler than the body post. take a real link post,
keep the link, author, and title the same, and generate a new comments section for that post,
with some real and some newly fake, given the real and fake users.

generate_fake_body_post(real_body_post)
this is more complex. at first it could be done the same way as the link,
with the author, title, and body kept the same, but eventually, could generate fake body posts as well, given real world context.


