/*

A collection of functions used to complete user pools and content string lists
from information retrieved in the original scraping process,
and migrate them to a format for running the model.

*/

const hnAPIFunctions = require("./hnAPIFunctions");
const utilities = require("./utilities");
const scrapeHN = require("./scrapeHN");
const dbUtils = require("./dbUtils");

const fs = require("fs").promises;


/*

    Complete a record for an original post, to be inserted into the database.

*/

function completeOriginalPost(originalPost){
    const completePostObject = {
        by: originalPost.item.by,
        id: originalPost.item.id,
        score: originalPost.item.score,
        time: originalPost.item.time,
        title: originalPost.item.title,
        text: originalPost.item.text ?? "",
        url: originalPost?.linkContent?.link ?? "",
        urlContent: originalPost?.linkContent?.content ?? ""
    }
    return completePostObject;
}


/*
    Take an original list of posts, and convert it to a list of solely post objects,
    to be inserted into the database.
*/

function completeOriginalPostList(originalCSList){

    const completePostList = [];

    for(let i = 0; i < originalCSList.length; i++){
        const anticipatedErrorCondition = originalCSList[i].error;
        const itemUndefined = originalCSList[i].item === undefined;
        const idUndefined = originalCSList[i].item?.id === undefined;
        const byUndefined = originalCSList[i].item?.by === undefined;
        const timeUndefined = originalCSList[i].item?.time === undefined;
        const titleUndefined = originalCSList[i].item?.title === undefined;
        const scoreUndefined = originalCSList[i].item?.score === undefined;
        const typeUndefined = originalCSList[i].item?.type === undefined;
        const notOfTypeStory = originalCSList[i].item?.type !== "story";

        const errorConditions = {anticipatedErrorCondition, itemUndefined, idUndefined, byUndefined, timeUndefined, titleUndefined, scoreUndefined, typeUndefined, notOfTypeStory};

        const filterCondition = Object.values(errorConditions).reduce((acc, e) => acc || e, false);

        try {
            if (!filterCondition){
                const completePost = completeOriginalPost(originalCSList[i]);
                completePostList.push(completePost);
            }else {
                throw `Post error: ${JSON.stringify(errorConditions)}`;
            }
        }catch (err){
            console.log(`Error in generating final post for id ${originalCSList[i].id ?? "Unknown"}, skipping.`);
            console.log(err);
        } 
    }

    return completePostList;

}


/*
    Complete an original comment to a format which can be inserted into the database.
*/

function completeOriginalComment(originalComment){
    const completeCommentObject = {
        by: originalComment.item.by,
        id: originalComment.item.id,
        text: originalComment.item.text,
        time: originalComment.item.time
    }

    return completeCommentObject;
}

/*

    Complete an original list of comments into a final list to be inserted into the database.

*/
function completeOriginalCommentList(originalCommentList){
    const completeCommentList = [];

    for(let i = 0; i < originalCommentList.length; i++){
        const anticipatedErrorCondition = originalCommentList[i].error;
        const itemUndefined = originalCommentList[i].item === undefined;
        const idUndefined = originalCommentList[i].item?.id === undefined;
        const byUndefined = originalCommentList[i].item?.by === undefined;
        const timeUndefined = originalCommentList[i].item?.time === undefined;
        const textUndefined = originalCommentList[i].item?.text === undefined;
        const typeUndefined = originalCommentList[i].item?.type === undefined;
        const notOfTypeComment = originalCommentList[i].item?.type !== "comment";

        const errorConditions = {anticipatedErrorCondition, itemUndefined, idUndefined, byUndefined, timeUndefined, textUndefined, typeUndefined, notOfTypeComment};

        const filterCondition = Object.values(errorConditions).reduce((acc, e) => acc || e, false);

        try {
            if (!filterCondition){
                const completeComment = completeOriginalComment(originalCommentList[i]);
                completeCommentList.push(completeComment);
            }else {
                throw `Comment error: ${JSON.stringify(errorConditions)}`;
            }
        }catch (err){
            console.log(`Error in generating final comment for id ${originalCommentList[i].id ?? "Unknown"}, skipping.`);
            console.log(err);
        } 
    }

    return completeCommentList;
}

/*
    Take a given user retrieved in the scraping pipeline,
    complete their initial profile, and return a final user object,
    to be inserted into the database.
*/
async function completeUserProfile(scrapedUserObject){

    console.log(`\nCompleting user profile for user ${scrapedUserObject.id}...\n`);

    //get original info from user object
    const originalUser = {
        username: scrapedUserObject.id,
        about: scrapedUserObject.about ?? "",
        karma: scrapedUserObject.karma ?? 0,
        submitted: scrapedUserObject.submitted ?? [],
        created: scrapedUserObject.created
    };

    const finalUser = {
        userProfile: {
            username: originalUser.username,
            about: originalUser.about,
            karma: originalUser.karma,
            created: originalUser.created,
            postIDs: [],
            commentIDs: [],
            favoritePostIDs: [],
            textSamples: [],
            interests: [],
            beliefs: []
        },
        posts: [],
        comments: []
    }

    //scrape the user's favorites from Hacker News HTML
    //TODO: maybe also scrape the comments?

    const rawFavoritePostIDs = await scrapeHN.grabUserFavorites(originalUser.username);

    console.log(`Grabbing favorite posts for user ${originalUser.username}...`);
    //grab raw post items
    const originalFavoritePosts = await hnAPIFunctions.grabListOfItems(rawFavoritePostIDs.slice(0, 1e9), 400);
    //fill link content
    console.log(`Grabbing link content for favorite posts...`);
    const favoritePostsWithLinkContent = await scrapeHN.grabLinkContentForPostList(originalFavoritePosts, 200);
 
    const completedFavoritePosts = completeOriginalPostList(favoritePostsWithLinkContent);
    const completedFavoritePostIDs = completedFavoritePosts.map(p => p.id);

    finalUser.posts = completedFavoritePosts;
    finalUser.userProfile.favoritePostIDs = completedFavoritePostIDs;

    //retrieve the body of IDs from their post history.

    console.log(`Grabbing submissions from user ${originalUser.username}...`);

    const submissions = await hnAPIFunctions.grabListOfItems(originalUser.submitted.slice(0, 1e9), 200);

    //this is scuffed
    const originalComments = submissions.filter(s => !s.error && s.item !== undefined && s.item?.type === "comment");

    const completedComments = completeOriginalCommentList(originalComments);
    const completedCommentIDs = completedComments.map(c => c.id);
    finalUser.comments = completedComments;
    finalUser.userProfile.commentIDs = completedCommentIDs;

    //also scuffed
    let originalPosts = submissions.filter(s => !s.error && s.item !== undefined && s.item?.type === "story");
    originalPosts = await scrapeHN.grabLinkContentForPostList(originalPosts);
    const completedPosts = completeOriginalPostList(originalPosts);
    const completedPostIDs = completedPosts.map(p => p.id);
    finalUser.posts = [...finalUser.posts, ...completedPosts];
    finalUser.userProfile.postIDs = completedPostIDs;

    return finalUser;
}

/*
    Take a given user pool retrieved in the original scraping pipeline,
    and convert it to a list of completed user profiles
*/

async function completeListOfUserProfiles(originalUserPool){
    
    const userProfiles = [];
    const usernames = [];
    let posts = [];
    let comments = [];
    for(let i = 0; i < originalUserPool.length; i++){
        //check for registered error and unforeseen strange errors
        const anticipatedErrorCondition = originalUserPool[i].error;
        const userUndefined = originalUserPool[i].user === undefined;
        const idUndefined = originalUserPool[i]?.user.id === undefined;
        const createdUndefined = originalUserPool[i]?.user.created === undefined;

        const errorConditions = {anticipatedErrorCondition, userUndefined, idUndefined, createdUndefined};

        const filterCondition = Object.values(errorConditions).reduce((acc, e) => acc || e, false);

        try {
            if (!filterCondition){
                const completeUserObject = await completeUserProfile(originalUserPool[i].user);
                userProfiles.push(completeUserObject.userProfile);
                usernames.push(completeUserObject.userProfile.username);
                posts = [...posts, ...completeUserObject.posts];
                comments = [...comments, ...completeUserObject.comments];
            }else {
                throw `User error: ${JSON.stringify(errorConditions)}`;
            }
        }catch (err){
            console.log(`Error in generating final user profile for username ${originalUserPool[i].username ?? "Unknown"}.`);
            console.log(err);
        }
    }

    return {
        userProfiles,
        usernames,
        posts,
        comments
    };
}


function recFlattenComments(commentList){
    const children = commentList.filter(c => !c.error && c.item !== undefined && c.item?.childComments !== undefined).map(c => recFlattenComments(c.item.childComments)).flat(Infinity);
    return [...commentList, ...children];
}

/*
    Take a list of posts from the original dataset, map everything to just ids.
    Only run recursively on a child if they are present in the complete comments array,
    to ensure during runtime that all ids map to comments in the database.
*/
function extractContentStringTree(originalItems, completedCommentIDs){
    const filteredItems = originalItems.filter(i => i?.item?.id !== undefined && completedCommentIDs.filter(c => i.item.id).length !== 0);

    const csLists = filteredItems.map(i => {return {id: i.item.id, kids: i?.item?.childComments !== undefined ? extractContentStringTree(i.item.childComments, completedCommentIDs) : []}});

    return csLists;
}

/*
    Given an original post object, 
    convert it to a list of posts and comments to be inserted into the database, 
    and a list of content strings with IDs to be used in running the model.
*/
function completeContentString(originalPost){

    const anticipatedErrorCondition = originalPost.error;
    const itemUndefined = originalPost.item === undefined;
    const idUndefined = originalPost.item?.id === undefined;
    const byUndefined = originalPost.item?.by === undefined;
    const timeUndefined = originalPost.item?.time === undefined;
    const titleUndefined = originalPost.item?.title === undefined;
    const scoreUndefined = originalPost.item?.score === undefined;
    const typeUndefined = originalPost.item?.type === undefined;
    const notOfTypeStory = originalPost.item?.type !== "story";

    const errorConditions = {anticipatedErrorCondition, itemUndefined, idUndefined, byUndefined, timeUndefined, titleUndefined, scoreUndefined, typeUndefined, notOfTypeStory};

    const filterCondition = Object.values(errorConditions).reduce((acc, e) => acc || e, false);

    if (filterCondition){
        throw `Root post error: ${JSON.stringify(errorConditions)}`;
    }

    const posts = [completeOriginalPost(originalPost)];

    //get flat list of comments to be put in database and complete them

    const originalPostComments = originalPost.comments;

    const flattenedComments = recFlattenComments(originalPostComments);

    const comments = completeOriginalCommentList(flattenedComments);

    const commentIDs = comments.map(c => c.id);

    //get content strings as a tree of ids
    const contentStrings = {id: originalPost.item.id, kids: extractContentStringTree(originalPostComments, commentIDs)};

    return {
        posts,
        comments,
        contentStrings
    };
}



/*
    Take an original dataset, and convert it into a objects to be inserted into the database,
    and lists of ids representing user pools and content strings,
    to be used in running the model.

    This is done in batches as there are a lot of users.
*/
async function completeBatchOfOriginalDataset(originalDatasetName, userBatchSize, postsBatchSize){

    console.log(`Completing batch of ${userBatchSize} users and ${postsBatchSize} posts from original dataset ${originalDatasetName}...`);

    let usernames = [];
    let contentStringLists = [];
    let userProfiles = [];
    let posts = [];
    let comments = [];

    const originalDatasetPath = `./datasets/${originalDatasetName}.json`;
    const originalDataset = await utilities.readJsonFile(originalDatasetPath);

    const originalUserPool = originalDataset.userPool;

    const currentUserPoolBatch = originalUserPool.slice(0, userBatchSize);

    const restOfUserPool = originalUserPool.slice(userBatchSize, 1e9);

    const allUserData = await completeListOfUserProfiles(currentUserPoolBatch);
    
    usernames = allUserData.usernames;
    userProfiles = allUserData.userProfiles;
    posts = [...posts, allUserData.posts];
    comments = [...comments, allUserData.comments];

    const originalPostList = originalDataset.posts;

    const currentPostBatch = originalPostList.slice(0, postsBatchSize);
    const restOfPosts = originalPostList.slice(postsBatchSize, 1e9);

    for(let i = 0; i < currentPostBatch.length; i++){
        try {
            const completeCS = completeContentString(currentPostBatch[i]);
            posts = [...posts, ...completeCS.posts];
            comments = [...comments, ...completeCS.comments];
            contentStringLists = [...contentStringLists, completeCS.contentStrings];
        }catch (err){
            console.log(err);
            console.log("Skipping...");
            continue;
        }
    }

    //create directory for complete dataset,
    //add posts, users, and comments to database, 
    //and leave content string lists and users as jsons to be 
    //used in running the model.
    await utilities.createDirectory(`./completeDatasets/${originalDatasetName}`);

    //create database
    const dbPath = `./completeDatasets/${originalDatasetName}/database`;
    await dbUtils.initializeDB(dbPath);
    
    //add stuff
    await dbUtils.insertUserProfiles(dbPath, userProfiles);
    await dbUtils.insertPosts(dbPath, posts.flat(Infinity));
    await dbUtils.insertComments(dbPath, comments.flat(Infinity));

    //write jsons for running model

    const completedUsernamesPath = `./completeDatasets/${originalDatasetName}/usernames.json`;
    const completedContentStringsPath = `./completeDatasets/${originalDatasetName}/contentStringLists.json`;

    const usernamesExists = await utilities.checkFileIfExists(completedUsernamesPath);
    const contentStringsExists = await utilities.checkFileIfExists(completedContentStringsPath);

    if (usernamesExists){
        const existingCompleteUsernames = await utilities.readJsonFile(completedUsernamesPath);
        usernames = [...existingCompleteUsernames, ...usernames].flat(Infinity);
    }

    await utilities.writeJsonToFile(usernames, completedUsernamesPath);

    if (contentStringsExists){
        const existingCompleteContentStrings = await utilities.readJsonFile(completedContentStringsPath);
        contentStringLists = [...existingCompleteContentStrings, ...contentStringLists];
    }

    await utilities.writeJsonToFile(contentStringLists, completedContentStringsPath);

    //modify old dataset to include users and posts not in current batch, if there are still some left

    await fs.unlink(originalDatasetPath);

    if (restOfPosts.length !== 0 || restOfUserPool.length !== 0){
        const incompleteOriginalDataset = {
            posts: restOfPosts,
            userPool: restOfUserPool
        }

        await utilities.writeJsonToFile(incompleteOriginalDataset, originalDatasetPath);

        console.log(`Successfully completed ${usernames.length} user records and ${contentStringLists.length} content strings from dataset ${originalDatasetName}`);
        return false;
    }else {
        console.log(`Successfully completed dataset ${originalDatasetName}.`);
        return true;
    }
}

async function completeOriginalDataset(originalDatasetName, userBatchSize, postsBatchSize){
    let currentBatchDone = await completeBatchOfOriginalDataset(originalDatasetName, userBatchSize, postsBatchSize);
    for(let i = 1; !currentBatchDone; i++){
        console.log(`Starting batch ${i} of ${originalDatasetName}`);
        currentBatchDone = await completeBatchOfOriginalDataset(originalDatasetName, userBatchSize, postsBatchSize);
    }
}

/*
    Complete an array of original datasets
*/
async function completeOriginalDatasetList(originalDatasetNames, userBatchSize, postsBatchSize){
    for(let i = 0; i < originalDatasetNames.length; i++){
        await completeOriginalDataset(originalDatasetNames[i], userBatchSize, postsBatchSize);
    }
}

/*
    Complete all original datasets stored locally.
*/
async function completeAllCurrentOriginalDatasets(userBatchSize, postsBatchSize){
    const allDatasets = await utilities.getFiles("./datasets");

    const originalDatasetNames = allDatasets.map(name => name.split(".json")[0]);

    completeOriginalDatasetList(originalDatasetNames, userBatchSize, postsBatchSize);
}

async function main(){
    const helpMessage = "USAGE: \n <USER_BATCH_SIZE> <POST_BATCH_SIZE>";

    const USER_BATCH_SIZE = parseInt(process.argv[2]);
    const POST_BATCH_SIZE = parseInt(process.argv[3]);

    if (process.argv.length !== 4 || USER_BATCH_SIZE < 1 || POST_BATCH_SIZE < 1 || USER_BATCH_SIZE === NaN || POST_BATCH_SIZE === NaN){
        console.log(helpMessage);
        return;
    }

    await completeAllCurrentOriginalDatasets(USER_BATCH_SIZE, POST_BATCH_SIZE);

    
}

main();
