/*

A script to get a completed dataset of specified parameters

(Have to do this because heap issues even with batched completion of original datasets)

*/

const utilities = require("./utilities");


/*
    Fully complete an original dataset, given a user and post batch size.
*/
async function completeOriginalDataset(originalDatasetName, userBatchSize, postsBatchSize){

    const completeDatasetDir = `./completeDatasets/${originalDatasetName}`;

    await utilities.createDirectory(completeDatasetDir);

    let isNotDone = true;
    let batchNum = 0;

    do {
        console.log(`Starting batch ${batchNum} of ${originalDatasetName}...`);

        const batchName = `BATCH-${batchNum}`;

        const command = `node ./completeOriginalDatasetBatch.js ${originalDatasetName} ${batchName} ${userBatchSize} ${postsBatchSize} `;

        console.log(command);
        await utilities.runCommand(command);

        isDone = await utilities.checkFileIfExists(`./datasets/${originalDatasetName}.json`);
        ++batchNum;

    }while (isNotDone);

    console.log(`Finished completing dataset ${originalDatasetName}.`);
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
    const helpMessage = "USAGE: <DATASET_NAME> <USER_BATCH_SIZE> <POSTS_BATCH_SIZE>";

    if (process.argv.length != 5){
        console.log(helpMessage);
        return;
    }

    const originalDatasetName = process.argv[2];
    const userBatchSize = parseInt(process.argv[3]);
    const postsBatchSize = parseInt(process.argv[4]);
    
    await completeOriginalDataset(originalDatasetName, userBatchSize, postsBatchSize);
}

main();