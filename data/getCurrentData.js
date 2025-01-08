/*

    A script to scrape the current Hacker News best stories and convert them
    into a dataset for the experiment.

*/


const scrapeHN = require("./scrapeHN");

async function main(){
    await scrapeHN.runFullPipelineOnCurrentFP(false);
}

main();