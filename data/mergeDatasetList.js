/*
    A script to merge a number of given complete datasets.
*/

const mergeDatasets = require("./mergeDatasets");

async function main(){
    const helpMessage = "USAGE: <FINAL_NAME> <COMPLETE_DATASET_NAME> ...";

    const finalName = process.argv[2];
    const completeDatasetNames = process.argv.slice(3, 1e9);

    await mergeDatasets.mergeDatasetList(completeDatasetNames, finalName);
}

main();