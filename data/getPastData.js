/*

    A script to scrape past Hacker News front page data in a given date range.

*/

const scrapeHN = require("./scrapeHN");
const utilities = require("./utilities");

async function main(){

    const helpMessage = "USAGE:\n<startYear> <startMonth> <startDay> <endYear> <endMonth> <endDay>";

    const startYear = parseInt(process.argv[2]);
    const startMonth = parseInt(process.argv[3]);
    const startDay = parseInt(process.argv[4]);
    const endYear = parseInt(process.argv[5]);
    const endMonth = parseInt(process.argv[6]);
    const endDay = parseInt(process.argv[7]);

    const startDate = {
        year: startYear,
        month: startMonth,
        day: startDay
    };

    const endDate = {
        year: endYear, 
        month: endMonth,
        day: endDay
    };

    const k = 2;
    const dateRanges = utilities.getDateRange(startDate, endDate).reduce((acc, date) => acc.length != 0 && acc[0].length < k ? [[...acc[0], date], ...acc.slice(1)] : [[date], ...acc], []);

    for(let i = 0; i < dateRanges.length; i++){
        await scrapeHN.runFullPipelineOnPastFPs(dateRanges[i][0], dateRanges[i][dateRanges[i].length - 1], false);
    }
}

main();