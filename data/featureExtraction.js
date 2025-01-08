/*

A collection of functions used to extract features from the raw datasets
retrieved in the scraping pipeline

*/

const hnAPIFunctions = require("./hnAPIFunctions");
const utilities = require("./utilities");
const scrapeHN = require("./scrapeHN")


/*
    Take a given user retrieved in the scraping pipeline,
    and convert it into a final user object to be used in both determination and generation.
*/
async function createUserProfile(scrapedUserObject){
    //get original info from user object
    const originalUser = {
        username: scrapedUserObject.id,
        about: scrapedUserObject.about ?? "",
        karma: scrapedUserObject.karma ?? 0,
        submitted: scrapedUserObject.submitted ?? [],
        created: scrapedUserObject.created
    };

    const finalUser = {
        externalData: {
            username: originalUser.username,
            about: originalUser.about,
            karma: originalUser.karma,
            created: originalUser.created
        },
        internalData: {
            recentUsage: {
                linkPosts: 0,
                textPosts: 0,
                comments: 0
            },
            text_samples: [],
            interests: [],
            beliefs: []
        }
        
    }

    //scrape the user's favorites from Hacker News HTML
    //TODO: maybe also scrape the comments?

    const favoritePostIDs = await scrapeHN.grabUserFavorites(originalUser.username);
    const favoritePosts = await hnAPIFunctions.grabListOfItems(favoritePostIDs, 200);

    //retrieve the body of IDs from their post history.

    const submissions = await hnAPIFunctions.grabListOfItems(originalUser.submitted);
    const filteredSubmissions = submissions.filter(s => !s.error && s.item !== undefined).map(s => s.item);
    const comments = filteredSubmissions.filter(s => s.type === "comment");
    const posts = filteredSubmissions.filter(s => s.type === "story");

    //sort posts by links and text, and grab link content for link posts.
    const linkPosts = await scrapeHN.grabLinkContentForPostList(posts.filter(p => p.url !== undefined));
    const textPosts = posts.filter(p => p.text !== undefined);

    //set recent usage statistics
    //start with only including the past month
    //TODO: change?
    const currentTimestamp = Math.floor(Date.now() / 1000);
    const oneMonth = 60 * 60 * 24 * 30;
    const recentCutoff = currentTimestamp - oneMonth;

    finalUser.internalData.recentUsage.linkPosts = linkPosts.filter(p => p.time > recentCutoff);
    finalUser.internalData.recentUsage.textPosts = textPosts.filter(p => p.time > recentCutoff);
    finalUser.internalData.recentUsage.comments = comments.filter(c => c.time > recentCutoff);

    //rest is with an LLM...


}

/*
    Take a given user pool retrieved in the original scraping pipeline,
    and convert it to a final list of users.
*/

async function createFinalUserPool(originalUserPool){
    const finalUsers = [];
    for(let i = 0; i < originalUserPool.length; i++){
        //check for registered error and unforeseen strange errors
        const anticipatedErrorCondition = originalUserPool[i].error;
        let unanticipatedErrorCondition = originalUserPool[i].user === undefined;
        unanticipatedErrorCondition ||= originalUserPool[i].user?.id === undefined;
        unanticipatedErrorCondition ||= originalUserPool[i].user?.created === undefined;
        const errorCondition = anticipatedErrorCondition || unanticipatedErrorCondition;
        try {
            if (!errorCondition){
                const finalUser = await createUserProfile(originalUserPool[i].user);
                finalUsers.push(finalUser);
            }else {
                throw "";
            }
        }catch (err){
            console.log(`Error in generating final user profile for username ${originalUserPool.username ?? "Unknown"}, skipping`);
        }
    }

    return finalUsers;
}

/*
    Migrate a portion of a user pool from an originally scraped dataset
    of a given path to a new users array to be used in running the models.
*/
async function migrateOriginalUserpool(originalDatasetName, usersDatasetName, numUsers){
    const originalDataset = await utilities.readJsonFile(`./datasets/${originalDatasetName}.json`);

    const originalUserPool = originalDataset.userPool.slice(0, numUsers);

    const finalUserPool = await createFinalUserPool(originalUserPool);

    await utilities.writeJsonToFile(finalUserPool, `./users/${usersDatasetName}.json`);
    
    return finalUserPool;
}

async function main(){
    const testFinalUserPool = await migrateOriginalUserpool("2024-12-4to2024-12-6", "test", 1);

    console.log(testFinalUserPool);
}

main();
