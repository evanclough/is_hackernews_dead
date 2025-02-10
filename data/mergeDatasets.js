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

    const leftCSLPath = `./completeDatasets/${leftDataset}/prf.json`;
    const rightCSLPath = `./completeDatasets/${rightDataset}/prf.json`;

    const leftUsernames = await utilities.readJsonFile(leftUsernamesPath);
    const rightUsernames = await utilities.readJsonFile(rightUsernamesPath);
    const leftCSL = await utilities.readJsonFile(leftCSLPath);
    const rightCSL = await utilities.readJsonFile(rightCSLPath);
    
    const mergedUsernameList = utilities.removeDuplicateAtoms([...leftUsernames, ...rightUsernames]);
    //for the content strings, we only have ot filter by root posts.
    const mergedContentStringList = utilities.removeDuplicateObjectsByKeySeq([...leftCSL, ...rightCSL], ["id"]);

    //write final jsons
    await utilities.writeJsonToFile(mergedUsernameList, `./completeDatasets/${finalName}/usernames.json`);
    await utilities.writeJsonToFile(mergedContentStringList, `./completeDatasets/${finalName}/prf.json`);

    //merge the contents of the two databases
    const leftDBPath = `./completeDatasets/${leftDataset}/data.db`;
    const rightDBPath = `./completeDatasets/${rightDataset}/data.db`;
    const finalDBPath = `./completeDatasets/${finalName}/data.db`;

    await dbUtils.mergeDatabases(leftDBPath, rightDBPath, finalDBPath);

    //remove old directories
    await fs.rm(`./completeDatasets/${leftDataset}`, { recursive: true, force: true });
    await fs.rm(`./completeDatasets/${rightDataset}`, { recursive: true, force: true });

    console.log(`Successfully merged datasets ${rightDataset} and ${leftDataset}.`);
    
}

/*
    Merge an array of completed datasets.
*/
async function mergeDatasetList(completeDatasets, finalName){
    if (completeDatasets.length < 2){
        throw "Error: cannot merge list of datasets with length smaller than two.";
    }

    let currentIncompleteDatasets = [...completeDatasets];
    let i = 0;

    while (currentIncompleteDatasets.length > 1){
        console.log(`${i} ${currentIncompleteDatasets}`);
        const currentIntermediaryNames = [];

        for(let j = 1; j < currentIncompleteDatasets.length; j+=2){
            const currentIntermediaryName = currentIncompleteDatasets.length == 2 ? finalName : `${finalName}-MERGE${i}-${j}`;
            currentIntermediaryNames.push(currentIntermediaryName);
            await mergeDatasets(currentIncompleteDatasets[j - 1], currentIncompleteDatasets[j], currentIntermediaryName);
        }

        if (currentIncompleteDatasets.length % 2 === 1){
            currentIntermediaryNames.push(currentIncompleteDatasets[currentIncompleteDatasets.length - 1]);
        }

        currentIncompleteDatasets = [...currentIntermediaryNames];
        ++i;
    }
}

/*
    Merge all completed datasets stored in a given directory
*/
async function mergeDirectory(dirName){
    const completeDatasetNames = await utilities.getDirectories(`./completeDatasets/${dirName}`);

    const completeDatasets = completeDatasetNames.map(n => `${dirName}/${n}`);

    const tempMergePath = `${dirName}/TEMP`;

    await mergeDatasetList(completeDatasets, tempMergePath);

    await fs.copyFile(`./completeDatasets/${tempMergePath}/usernames.json`, `./completeDatasets/${dirName}/usernames.json`);
    await fs.copyFile(`./completeDatasets/${tempMergePath}/prf.json`, `./completeDatasets/${dirName}/prf.json`);
    await fs.copyFile(`./completeDatasets/${tempMergePath}/data.db`, `./completeDatasets/${dirName}/data.db`);
    await fs.rm(`./completeDatasets/${tempMergePath}`, { recursive: true, force: true });
}

module.exports = {
    mergeDirectory,
    mergeDatasetList
}