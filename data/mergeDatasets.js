/*

    A set of functions to take raw, scraped datasets and refine them 
    for training/testing our model by reformatting and adding necessary features.

*/

const utilities = require("./utilities");
const dbUtils = require("./dbUtils");

const fs = require("fs").promises;

/*

    Merge two datasets by combining the contents of their two databases,
    their username lists, and content string lists.

    The final name must not be equal to either of names of the datasets being merged.

*/
async function mergeDatasets(leftDataset, rightDataset, finalName){
    if (leftDataset === finalName || rightDataset === finalName){
        throw "The final name must not be equal to either of names of the datasets being merged.";
    }

    await utilities.createDirectory(`./completeDatasets/${finalName}`);

    const leftUsernamesPath = `./completeDatasets/${leftDataset}/usernames.json`;
    const rightUsernamesPath = `./completeDatasets/${rightDataset}/usernames.json`;

    const leftCSLPath = `./completeDatasets/${leftDataset}/contentStringLists.json`;
    const rightCSLPath = `./completeDatasets/${rightDataset}/contentStringLists.json`;

    const leftUsernames = await utilities.readJsonFile(leftUsernamesPath);
    const rightUsernames = await utilities.readJsonFile(rightUsernamesPath);
    const leftCSL = await utilities.readJsonFile(leftCSLPath);
    const rightCSL = await utilities.readJsonFile(rightCSLPath);
    
    const mergedUsernameList = utilities.removeDuplicateAtoms([...leftUsernames, ...rightUsernames]);
    //for the content strings, we only have ot filter by root posts.
    const mergedContentStringList = utilities.removeDuplicateObjectsByKeySeq([...leftCSL, ...rightCSL], ["id"]);

    //write final jsons
    await utilities.writeJsonToFile(mergedUsernameList, `./completeDatasets/${finalName}/usernames.json`);
    await utilities.writeJsonToFile(mergedContentStringList, `./completeDatasets/${finalName}/contentStringLists.json`);

    //remove old directories
    //await fs.rm(`./completeDatasets/${leftDataset}`, { recursive: true, force: true });
    //await fs.rm(`./completeDatasets/${rightDataset}`, { recursive: true, force: true });

    //merge the contents of the two databases
    const leftDBPath = `./completeDatasets/${leftDataset}/database.db`;
    const rightDBPath = `./completeDatasets/${rightDataset}/database.db`;
    const finalDBPath = `./completeDatasets/${finalName}/database.db`;

    await dbUtils.mergeDatabases(leftDBPath, rightDBPath, finalDBPath);

    console.log(`Successfully merged datasets ${rightDataset} and ${leftDataset}.`);
    
}

/*

    Merge an array of completed datasets.

*/
async function mergeDatasetList(completeDatasets, finalName){
    if (completeDatasets.length < 2){
        throw "Error: cannot merge list of datasets with length smaller than two.";
    }
    
    await mergeDatasets(completeDatasets[0], completeDatasets[1], finalName);

    for(let i = 2; i < completeDatasets.length; i++){
        await fs.rename(`./completeDatasets/${finalName}`, `./completeDatasets/temp`);
        finalDataset = await mergeDatasets("temp", completeDatasets[i], finalName);
    }

}

/*

    Merge all completed datasets currently stored locally.

*/
async function mergeAllCompletedDatasets(finalName){
    const completeDatasets = await utilities.getDirectories("./completeDatasets");

    await mergeDatasetList(completeDatasets, finalName);
}


async function main(){
    await mergeDatasetList(["2024-11-7to2024-11-8", "2024-11-8to2024-11-9"], "test3");
    //await mergeAllCompletedDatasets("test");
}

main();