/*

    Functions used to call the official Hacker News API.

*/

const axios = require('axios');

const utilities = require('./utilities');

/*
    Grabs an item from the official Hacker News API, given its ID.
*/
async function grabItemFromAPI(ID){
    //fill in the API url with the id
    const apiURL = `https://hacker-news.firebaseio.com/v0/item/${ID}.json?print=pretty`;
    //make request, return response if error, log it
    try {
        const apiResponse = await axios.get(apiURL);

        return apiResponse.data;
    }catch(err){
        console.log(`Error in fetching item with ID ${ID}: ${err}`);
        //propagate error upward
        throw err;
    }
}

/*
    Grabs a list of items, given their IDs.
*/
async function grabListOfItems(idList, interval){
    const items = [];

    for(let i = 0; i < idList.length; i++){
        try {
            const retrievedItem = await grabItemFromAPI(idList[i]);
            console.log(`Grabbed item with ID ${idList[i]} of type ${retrievedItem.type}`);
            console.log(`Item ${i} of ${idList.length}.\n`);
            items.push({error: false, id: idList[i], item: retrievedItem});
        }catch (err) {
            items.push({error: true, id: idList[i], item: {}});
        }

        await utilities.sleep(interval);
    }

    return items;
}

/*
    Grabs info on a given username.
*/
async function grabUserFromAPI(username){
    const apiURL = `https://hacker-news.firebaseio.com/v0/user/${username}.json?print=pretty`;
    //make request, return response if error, log it
    try {
        const apiResponse = await axios.get(apiURL);
        return apiResponse.data;
    }catch(err){
        console.log(`Error in fetching user with username ${username}: ${err}`);
        //propagate error upward
        throw err;
    }
}

/*
    Grabs info on a list of users, given their usernames.
*/
async function grabListOfUsers(usernameList, interval){
    const users = [];
    for(let i = 0; i < usernameList.length; i++){
        try {
            const retrievedUser = await grabUserFromAPI(usernameList[i]);

            console.log(`Grabbed user with username: ${usernameList[i]}`);
            console.log(`User ${i} of ${usernameList.length}\n`);

            users.push({error: false, username: usernameList[i], user: retrievedUser});
        }catch (err) {
            users.push({error: true, username: usernameList[i], user: {}});
        }
        
        await utilities.sleep(interval);
    }

    return users;
}

/*
    Fetch the current stories, according to specified descriptor
*/

async function grabCurrentStories(descriptor) {
    const descriptors = ["top", "best", "new", "ask", "show", "job"];

    if(descriptors.filter(d => d == descriptor).length == 0) {
        throw "Invalid descriptor passed to grabCurrentStories";
    }

    const apiURL = `https://hacker-news.firebaseio.com/v0/${descriptor}stories.json?print=pretty`;
    try {
        const apiResponse = await axios.get(apiURL);
        return apiResponse.data;
    }catch (err){
        console.log(`Error in fetching the current ${descriptor} stories.`);
        throw err;
    }
}

module.exports = {
    grabItemFromAPI,
    grabListOfItems,
    grabUserFromAPI,
    grabListOfUsers,
    grabCurrentStories
}