/*

    A set of functions to take raw, scraped datasets and refine them 
    for training/testing our model by reformatting and adding necessary features.

*/

const utilities = require("./utilities");


/*

    Merge two datasets by combining their posts and users, eliminating duplicates.

*/
async function mergeDatasets(leftDataset, rightDataset){

    const mergedPosts = utilities.removeDuplicateObjectsByKeySeq([...leftDataset.posts, ...rightDataset.posts], ["id"]);
    const mergedUserPool = utilities.removeDuplicateObjectsByKeySeq([...leftUserPool.userPool, ...rightUserPool.userPool], ["username"]);

    return {
        posts: mergedPosts,
        userPool: mergedUserPool
    };
}

/*

    Merge a list of datasets, and write it to a file, given a name.

*/
async function mergeDatasetList(datasets, name){
    
    const mergedDataset = datasets.reduce((acc, i) => mergeDatasets(acc, i), {posts: [], userPool: []});

    await utilities.writeJsonToFile(mergedDataset, `./datasets/${name}.json`);
}


/*
    Merge a list of dataset paths into one dataset, and write it to a file, given the list, and a final name.
*/

async function mergeDatasetPathList(datasetPaths, name){

    const datasets = [];
    for(let i = 0; i < datasetPaths.length; i++){
        try {
            const dataset = await utilities.readJsonFile(datasetPaths[i]);
            datasets.push(dataset);
        }catch (err){
            console.log(`Error in merging dataset with given path ${datasetPaths[i]}, skipping`);
            continue;
        }
    }

    await mergeDatasetList(datasets, name);
}

async function main(){
    await mergeDatasetPathList(["./datasets/2024-12-12to2024-12-15.json", "./datasets/2024-12-15to2024-12-18.json"], "test.json");
}

//main();