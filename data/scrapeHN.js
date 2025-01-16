/*
    A collection of functions which use the official Hacker News API 
    to collect data for various front pages, given their raw HTML.

    The code isn't as nice as I like right now because I've had some
    bad experiences in the past trying to use the new async list functions,
    but it'll do.
*/

const utilities = require('./utilities');
const hnAPIFunctions = require('./hnAPIFunctions');

/*
    Grab a user's favorites list from Hacker News HTML.
    (Sorry, I don't believe this is in the API)
    This is also not in the pipeline, as I want to save
    user data extraction for later, and I forgot about this originally.
*/
async function grabUserFavorites(username){
    const favoritesUrl = `https://news.ycombinator.com/favorites?id=${username}`;

    const nameString = `Favorites for user ${username}`;

    try {
        const favoritesHTML = await utilities.grabLinkContent(favoritesUrl);
        return utilities.scrapePostIDsFromHNPage(favoritesHTML, nameString);
    }catch (err){
        console.log(`Error scraping favorite posts from user ${username} - there are likely none.`);
        return [];
    }
}

/*
    Read in the raw HTML file for a front page on a given date.
*/
async function readFPHTMLFile(date){
    const dateString = utilities.getDateString(date);
    try {
        const html = await utilities.readFile(`./frontPageHTML/${dateString}.html`);
        return html;
    }catch (err){
        console.log(`Error in trying to read HTML for front page on ${dateString}, skipping`);
        return "";
    }
}

/*
    Convert the raw HTML of a front page for a given day 
    to a list of post IDs.
*/
function grabPostIDsForFP(htmlString, date){
    const dateString = utilities.getDateString(date);

    const nameString = `Front page on date ${dateString}`;

    const postIDFP = {
        date: {...date},
        postIDs: []
    };

    try {
        const postIDs = utilities.scrapePostIDsFromHNPage(htmlString, nameString);
        postIDFP.postIDs = postIDs;
    }catch (err){
        console.log(`Error in grabbing post IDs from front page on ${dateString}.`)
    }

    return postIDFP;
}

/*
    Get a list of post IDs from a date range of front pages.
*/
async function grabDateRangeOfFPPostIDs(startDate, endDate, writeToFile){
    
    const dateRange = utilities.getDateRange(startDate, endDate);
    const dateRangeString = utilities.getDateRangeString(startDate, endDate);

    const htmlStrings = [];

    for(let i = 0; i < dateRange.length; i++){
        const fpHTML = await readFPHTMLFile(dateRange[i]);
        htmlStrings.push(fpHTML);
    }

    const postIDFPList = {
        frontPages: htmlStrings.filter(htmlString => htmlString != "").map((htmlString, index) => grabPostIDsForFP(htmlString, dateRange[index]))
    };

    if (writeToFile){
        await utilities.writeJsonToFile(postIDFPList, `./frontPageJSON/${dateRangeString}/postIDFPList.json`);
    }

    return postIDFPList;
}


/*
    Make a post ID list to be fed into the pipeline
    with the current 200 best stories in the same format
    as I used previously.
*/
async function makeCurrentFPPostIDList(currentDate, datasetName, writeToFile){

    const currentBestStories = await hnAPIFunctions.grabCurrentStories("best");

    const postIDFPList = {
        frontPages: [{date: currentDate, postIDs: currentBestStories}]
    }

    if(writeToFile){
        await utilities.writeJsonToFile(postIDFPList, `./frontPageJSON/${datasetName}/postIDFPList.json`)
    }

    return postIDFPList;
}

/*
    Get all of the posts contained in a given list of front pages,
    represented by a list of post IDs
*/
async function grabPostsForFP(postIDFPList, interval){
    const dateString = utilities.getDateString(postIDFPList.date);

    console.log(`Grabbing posts for front page on ${dateString}...`);
    console.log(`Estimated time: ${interval  *  postIDFPList.postIDs.length / 1000}s`);

    const posts = await hnAPIFunctions.grabListOfItems(postIDFPList.postIDs, interval);

    const successRatioString = `${posts.filter(post => !post.error).length} / ${postIDFPList.postIDs.length}`;

    console.log(`Sucessfully grabbed ${successRatioString} posts for front page on: ${dateString}`);
    

    const postsFP = {
        date: {...postIDFPList.date},
        posts: posts
    };

    return postsFP;
}

/*

    Get the content for all posts in a given list of front pages.
    The given list contains post IDs for each post in each front page.

*/
async function grabPostsForFPList(postIDFPList, interval, datasetName, writeToFile){
    const postsFPList = {
        frontPages: []
    };

    for(let i = 0; i < postIDFPList.frontPages.length; i++){
        const postsFP = await grabPostsForFP(postIDFPList.frontPages[i], interval);

        postsFPList.frontPages.push(postsFP);
        
        if (writeToFile){
            await utilities.writeJsonToFile(postsFPList, `./frontPageJSON/${datasetName}/postsFPList.json`);
        }
    }
    
    return postsFPList;
}

/*
    Recursively grab all comments for a given post,
    along with all users who've interacted on the post.
*/
async function grabCommentsForPost(kidList, interval, depth){
    //retrieved comments from initial ID list
    const comments = await hnAPIFunctions.grabListOfItems(kidList.map(kid => kid.toString()), interval);

    let usernames = comments.filter(comment => !comment.error && comment?.item?.by).map(comment => comment.item.by);

    for(let i = 0; i < comments.length; i++){
        //had a few weird errors with the item being undefined,
        //still not sure why
        if (comments[i].error || comments[i].item == undefined){
            console.log(`Error with comment: ${comments[i]}, skipping`)
            continue;
        }else {
            console.log(`Fetching descendants of comment #${i} / ${kidList.length} with depth ${depth}...`);
            const recResult = await grabCommentsForPost(comments[i].item.kids ?? [], 200, depth + 1);
            comments[i].item.childComments = recResult.comments;
            usernames = [...usernames, ...recResult.usernames];
        }
    }

    const deduplicatedUsernames = utilities.removeDuplicateAtoms(usernames);

    return {
        comments: comments,
        usernames: deduplicatedUsernames
    };
}

/*
    Get all comments for all posts in a given front page, along with 
    a list of all unique usernames to be used later.
*/
async function grabCommentsForFP(postsFP, interval){

    const dateString = utilities.getDateString(postsFP.date);

    console.log(`Grabbing comments for front page on ${dateString}...`);

    const postsWithComments = [];
    let allUsernamesOnFP = [];

    for(let i = 0; i < postsFP.posts.length; i++){
        console.log(`Grabbing comments for post with id: ${postsFP.posts[i].id}...`);

        const postCommentsAndUsers = await grabCommentsForPost(postsFP.posts[i].error ? [] : (postsFP.posts[i].item.kids ?? []), interval, 0);
        
        allUsernamesOnFP = [...allUsernamesOnFP, ...postCommentsAndUsers.usernames];
        postsWithComments.push({...postsFP.posts[i], comments: postCommentsAndUsers.comments});
    }

    allUsernamesOnFP = [...allUsernamesOnFP, ...postsFP.posts.filter(post => !post.error && post?.item?.by).map(post => post.item.by)];

    const uniqueUsernamesOnFP = utilities.removeDuplicateAtoms(allUsernamesOnFP);

    console.log(`Sucessfully grabbed comments and usernames for front page on ${dateString}`);

    const commentsFP = {
        date: {...postsFP.date}, 
        posts: postsWithComments
    }

    return {
        frontPage: commentsFP,
        usernames: uniqueUsernamesOnFP
    };
}


/*
    Get all comments for all posts for a given list of front pages.
    The given front page list must contain post content.
    Also, retrieve a list of unique usernames who've either posted or commented
    on the list of front pages.
*/
async function grabCommentsForFPList(postsFPList, interval, datasetName, writeToFile){
    const commentsFPList = {
        frontPages: [],
        usernames: []
    };

    for(let i = 0; i < postsFPList.frontPages.length; i++){
        const commentsResult = await grabCommentsForFP(postsFPList.frontPages[i], interval);

        commentsFPList.frontPages.push(commentsResult.frontPage);
        commentsFPList.usernames = [...commentsFPList.usernames, ...commentsResult.usernames];
    }

    commentsFPList.usernames = utilities.removeDuplicateAtoms(commentsFPList.usernames.flat(Infinity));

    if (writeToFile){
        await utilities.writeJsonToFile(commentsFPList, `./frontPageJSON/${datasetName}/commentsFPList.json`);
    }

    return commentsFPList;
}

/*
    Conglomerate all users who've interacted on each front page
    in a given list of front pages.
*/
async function grabUsersForFPList(commentsFPList, interval, datasetName, writeToFile){
    console.log(`Grabbing users for ${datasetName}...`);

    console.log(`Estimated time: ${commentsFPList.usernames.length * interval / 1000}s`);
    const retrievedUsers = await hnAPIFunctions.grabListOfUsers(commentsFPList.usernames, 200);

    const successRatioString = `${retrievedUsers.filter(user => !user.error).length} / ${commentsFPList.usernames.length}`;

    console.log(`Successfully grabbed ${successRatioString} users for  ${datasetName}`);

    const usersFPList = {
        frontPages: commentsFPList.frontPages,
        date: commentsFPList.date,
        userPool: retrievedUsers
    };

    if (writeToFile){
        await utilities.writeJsonToFile(usersFPList, `./frontPageJSON/${datasetName}/usersFPList.json`);
    }

    return usersFPList;
}


/*
    Scrapes the content for a link associated with a Hacker News post.
*/
async function grabLinkContentForPost(url){
    return utilities.grabLinkContent(url);
}

/*
    Fetch the content present at the links for a given
    list of posts.

    There's a lot more that could be done here, 
    as of right now I'm just leaving the raw results from the 
    get request (with cheerio), and a good amount of them error. 
    A lot of these may have to be done manually.
*/
async function grabLinkContentForPostList(posts, interval){
    const postsWithLinkContent = [];

    for(let i = 0; i < posts.length; i++){
        const postWithLinkContent = {
            ...posts[i]
        };

        if (posts[i]?.item?.url){
            try {
                const linkContent = await grabLinkContentForPost(posts[i].item.url);
                console.log(`Successfully got link content for link ${posts[i].item.url} on post ${posts[i].id}`);
                postWithLinkContent.linkContent = {error: false, link: posts[i].item.url, content: linkContent.slice(0,10000000)};
            } catch (err) {
                console.log(`Error in fetching link content for link ${posts[i].item.url} on post ${posts[i].id}`);
                postWithLinkContent.linkContent = {error: true, link: posts[i].item.url, content: ""};
            }
        }else {
            postWithLinkContent.linkContent = {error: false, link: "", content: ""};
        }
        postsWithLinkContent.push(postWithLinkContent);
        await utilities.sleep(interval);
    }

    return postsWithLinkContent;
}


/*
    Go through a list of front pages,
    and fetch all content from links contained in posts.
*/
async function grabLinkContentForFPList(postsFPList, interval, datasetName, writeToFile) {
    const linkContentFPList = {
        frontPages: []
    };

    console.log(`Grabbing link content for ${datasetName}`);

    for(let i = 0; i < postsFPList.frontPages.length; i++){
        const postsWithLinkContent = await grabLinkContentForPostList(postsFPList.frontPages[i].posts, interval);
        
        const dateString = utilities.getDateString(postsFPList.frontPages[i].date);
        const successRatioString = `${postsWithLinkContent.filter(post => !post.linkContent.error && post.linkContent.link != "").length} / ${postsWithLinkContent.filter(post => post.linkContent.link != "").length}`;
        
        console.log(`Successfully retrieved content for ${successRatioString} link posts for FP on ${dateString}`);
        
        linkContentFPList.frontPages.push({...postsFPList.frontPages[i], posts: postsWithLinkContent});
        
        if(writeToFile){
            await utilities.writeJsonToFile(linkContentFPList, `./frontPageJSON/${datasetName}/linkContentFPList.json`);
        }
    }

    return linkContentFPList;
}

/*
    Create an initial dataset from a final scraped JSON with a given name,
    and write it to the datasets directory.
*/
async function createInitialDataset(finalScrapedJson, name){
    
    const frontPages = finalScrapedJson.frontPages;

    let uniquePosts = [];

    for(let i = 0; i < frontPages.length; i++){
        const filteredPosts = frontPages[i].posts.filter(post => !post.error);
        const deduplicatedPosts = utilities.removeDuplicateObjectsByKeySeq(filteredPosts, ["id"]);
        uniquePosts = [...uniquePosts, ...deduplicatedPosts];
    }

    const filteredUserPool = finalScrapedJson.userPool.filter(user => !user.error);

    const initialDataset = {
        posts: uniquePosts,
        userPool: filteredUserPool
    }
    
    await utilities.writeJsonToFile(initialDataset, `./datasets/${name}.json`);

    console.log(`Successfully created initial dataset with name ${name}.`);
}


/*
    Run the full scraping pipeline on a given list of post IDs, 
    and write the final result to a dataset of a given name.
*/
async function runFullPipeline(postIDFPList, intermediaryWrites, name){
    const postsFPList = await grabPostsForFPList(postIDFPList, 500, name, intermediaryWrites);
    
    const linkContentFPList = await grabLinkContentForFPList(postsFPList, 500, name, intermediaryWrites);

    const commentsFPList = await grabCommentsForFPList(linkContentFPList, 200, name, intermediaryWrites);

    const usersFPList = await grabUsersForFPList(commentsFPList, 200, name, intermediaryWrites);

    await createInitialDataset(usersFPList, name);
}


/*
    Run the full scraping pipeline for past front pages
    from a given start date to a given end date.

    TODO: This could be parallelized, the approach I took
    with doing each step for the entire range before 
    going to the next is unnecessary. But it'll do for now.
*/
async function runFullPipelineOnPastFPs(startDate, endDate, intermediaryWrites){
    const dateRangeString = utilities.getDateRangeString(startDate, endDate);

    console.log(`Running full scraping pipeline on front pages from ${dateRangeString}...`);

    if (intermediaryWrites){
        await utilities.createDirectory(`./frontPageJSON/${dateRangeString}`);
    }

    const postIDFPList = await grabDateRangeOfFPPostIDs(startDate, endDate, intermediaryWrites);

    await runFullPipeline(postIDFPList, intermediaryWrites, dateRangeString);

}

/*
    Run the full scraping pipeline on the current Hacker News Best Stories,
    given a name to write the dataset to.
*/
async function runFullPipelineOnCurrentFP(intermediaryWrites){
    const currentTimestamp = new Date();

    const currentDate = {
        year: currentTimestamp.getFullYear(),
        month: currentTimestamp.getMonth() + 1,
        day: currentTimestamp.getDate()
    }

    const dateString = utilities.getDateString(currentDate);

    if (intermediaryWrites){
        await utilities.createDirectory(`./frontPageJSON/${dateString}`);
    }

    const postIDFPList = await makeCurrentFPPostIDList(currentDate, dateString, intermediaryWrites);

    await runFullPipeline(postIDFPList, intermediaryWrites, dateString);
}

module.exports = {
    runFullPipelineOnCurrentFP,
    runFullPipelineOnPastFPs,
    grabUserFavorites,
    grabLinkContentForPostList
}