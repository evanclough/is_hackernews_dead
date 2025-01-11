/*

A collection of functions used to complete user pools and content string lists
from information retrieved in the original scraping process,
to prepare them to be inserted into the database.

*/

const hnAPIFunctions = require("./hnAPIFunctions");
const utilities = require("./utilities");
const scrapeHN = require("./scrapeHN");
const dbUtils = require("./dbUtils");


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
        let unanticipatedErrorCondition = originalCSList[i].item === undefined;
        unanticipatedErrorCondition ||= originalCSList[i].item?.id === undefined;
        unanticipatedErrorCondition ||= originalCSList[i].item?.by === undefined;
        unanticipatedErrorCondition ||= originalCSList[i].item?.time === undefined;
        unanticipatedErrorCondition ||= originalCSList[i].item?.title === undefined;
        unanticipatedErrorCondition ||= originalCSList[i].item?.score === undefined;
        unanticipatedErrorCondition ||= originalCSList[i].item?.type === undefined;

        const filterCondition = unanticipatedErrorCondition || anticipatedErrorCondition || originalCSList[i].item?.type !== "story";

        try {
            if (!filterCondition){
                const completePost = completeOriginalPost(originalCSList[i]);
                completePostList.push(completePost);
            }else {
                throw "";
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
        let unanticipatedErrorCondition = originalCommentList[i].item === undefined;
        unanticipatedErrorCondition ||= originalCommentList[i].item?.id === undefined;
        unanticipatedErrorCondition ||= originalCommentList[i].item?.time === undefined;
        unanticipatedErrorCondition ||= originalCommentList[i].item?.text === undefined;
        unanticipatedErrorCondition ||= originalCommentList[i].item?.by === undefined;

        const filterCondition = unanticipatedErrorCondition || anticipatedErrorCondition || originalCommentList[i].item?.type !== "comment";

        try {
            if (!filterCondition){
                const completeComment = completeOriginalComment(originalCommentList[i]);
                completeCommentList.push(completeComment);
            }else {
                throw "";
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
    const originalFavoritePosts = await hnAPIFunctions.grabListOfItems(rawFavoritePostIDs, 400);
    //fill link content
    console.log(`Grabbing link content for favorite posts...`);
    const favoritePostsWithLinkContent = await scrapeHN.grabLinkContentForPostList(originalFavoritePosts, 200);
 
    const completedFavoritePosts = completeOriginalPostList(favoritePostsWithLinkContent);
    const completedFavoritePostIDs = completedFavoritePosts.map(p => p.id);

    finalUser.posts = completedFavoritePosts;
    finalUser.userProfile.favoritePostIDs = completedFavoritePostIDs;

    //retrieve the body of IDs from their post history.

    console.log(`Grabbing submissions from user ${originalUser.username}...`);

    const submissions = await hnAPIFunctions.grabListOfItems(originalUser.submitted, 200);

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
        let unanticipatedErrorCondition = originalUserPool[i].user === undefined;
        unanticipatedErrorCondition ||= originalUserPool[i]?.user?.id === undefined;
        unanticipatedErrorCondition ||= originalUserPool[i]?.user?.created === undefined;
        const errorCondition = anticipatedErrorCondition || unanticipatedErrorCondition;
        try {
            if (!errorCondition){
                const completeUserObject = await completeUserProfile(originalUserPool[i].user);
                userProfiles.push(completeUserObject.userProfile);
                usernames.push(completeUserObject.userProfile.username);
                posts = [...posts, ...completeUserObject.posts];
                comments = [...comments, ...completeUserObject.comments];
            }else {
                throw "";
            }
        }catch (err){
            console.log(`Error in generating final user profile for username ${originalUserPool[i].username ?? "Unknown"},\nbody: ${JSON.stringify(originalUserPool[i])} skipping.`);
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
*/
function extractContentStringTree(originalItems){
    const filteredItems = originalItems.filter(i => i?.item?.id !== undefined);

    const csLists = filteredItems.map(i => {return {id: i.item.id, kids: i?.item?.childComments !== undefined ? extractContentStringTree(i.item.childComments) : []}});

    return csLists;
}

/*
    Given an original post object, 
    convert it to a list of posts and comments to be inserted into the database, 
    and a list of content strings with IDs to be used in running the model.
*/
function completeContentString(originalPost){

    const anticipatedErrorCondition = originalPost.error;
    let unanticipatedErrorCondition = originalPost.item === undefined;
    unanticipatedErrorCondition ||= originalPost?.item?.id === undefined;
    unanticipatedErrorCondition ||= originalPost?.item?.by === undefined;
    unanticipatedErrorCondition ||= originalPost?.item?.time === undefined;
    unanticipatedErrorCondition ||= originalPost?.item?.title === undefined;
    unanticipatedErrorCondition ||= originalPost?.item?.score === undefined;
    unanticipatedErrorCondition ||= originalPost?.item?.type === undefined;
    unanticipatedErrorCondition ||= originalPost?.comments === undefined;
    unanticipatedErrorCondition ||= originalPost?.item?.kids === undefined;

    const filterCondition = originalPost?.item?.type !== "story";

    if (anticipatedErrorCondition || unanticipatedErrorCondition || filterCondition){
        throw `Error in completing content string for id ${originalPost?.item?.id ?? "unknown"}\n body: ${JSON.stringify(originalPost)}`;
    }

    const posts = [completeOriginalPost(originalPost)];

    //get flat list of comments to be put in database and complete them

    const originalPostComments = originalPost.comments;

    const flattenedComments = recFlattenComments(originalPostComments);

    const comments = completeOriginalCommentList(flattenedComments);

    //get content strings as a tree of ids
    const contentStrings = {id: originalPost.item.id, kids: extractContentStringTree(originalPostComments)};

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
*/
async function completeOriginalDataset(originalDatasetName){

    let usernames = [];
    let contentStringLists = [];
    let userProfiles = [];
    let posts = [];
    let comments = [];

    const originalDataset = await utilities.readJsonFile(`./datasets/${originalDatasetName}.json`);
    
    const originalUserPool = originalDataset.userPool;
    const allUserData = await completeListOfUserProfiles(originalUserPool);
    
    usernames = allUserData.usernames;
    userProfiles = allUserData.userProfiles;
    posts = [...posts, allUserData.posts];
    comments = [...comments, allUserData.comments];
    
    const originalPostList = originalDataset.posts;
    for(let i = 0; i < originalPostList.length; i++){
        try {
            const completeCS = completeContentString(originalPostList[i]);
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
    await utilities.writeJsonToFile(usernames, `./completeDatasets/${originalDatasetName}/usernames.json`);
    await utilities.writeJsonToFile(contentStringLists, `./completeDatasets/${originalDatasetName}/contentStringLists.json`);

}

/*
    Finish the migration, put users, posts, and comments for a given dataset into a 
    SQLite database, and store the username list, representing the user pool,
    and the content string list, as jsons
*/
async function migrateToDatabase(datasetName){




    //redundant
    const contentStringLists = await utilities.readJsonFile(`./toDatabase/${datasetName}/contentStringLists.json`)
    const usernames = await utilities.readJsonFile(`./toDatabase/${datasetName}/usernames.json`);

    await writeJsonToFile(usernames, `./completeDatasets/${datasetName}/userPool.json`);
    await writeJsonToFile(contentStringLists, `./completeDatasets/${datasetName}/contentStrings.json`);
}

async function main(){
    await completeOriginalDataset("2024-11-8to2024-11-9");
}

main();
