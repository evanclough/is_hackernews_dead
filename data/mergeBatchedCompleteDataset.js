/*
    A script to merge all batches of a given complete dataset into one.
*/

const mergeDatasets = require("./mergeDatasets");

async function main(){
    const helpMessage = "USAGE: <COMPLETE_DATASET_NAME>";

    if (process.argv.length != 3){
        console.log(helpMessage);
        return;
    }

    const completeDatasetName = process.argv[2];

    await mergeDatasets.mergeDirectory(completeDatasetName);
}

main();