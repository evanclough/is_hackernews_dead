/*

    A script to scrape the raw HTML data for past Hacker News front pages.

*/

const utilities = require('./utilities');

/*
    Grab the raw HTML for a past Hacker News front page,
    at a given date.
*/
async function grabFPRawHTML(date){

    const dateString = utilities.getDateString(date);

    const frontPageURL = `https://news.ycombinator.com/front?day=${dateString}`;

    try {
        const rawHTML = await utilities.grabLinkContent(frontPageURL);
        await utilities.writeStringToFile(rawHTML, `./frontPageHTML/${dateString}.html`);
    } catch (err) {
        console.log(`Error fetching popular page for ${dateString}, trying again soon`);
        throw err;
    }
}

/*
    Grab the raw HTML for Hacker News front pages from
    a given start date, to a given end date.
*/
async function grabDateRangeFPRawHTML(startDate, endDate, interval){
    const dateRange = utilities.getDateRange(startDate, endDate);
    for(let i = 0; i < dateRange.length; i++){
        try {
            await grabFPRawHTML(dateRange[i]);
        }catch (err) {
            i--;
        }

        await utilities.sleep(interval);
    }
}

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

    await grabDateRangeFPRawHTML(startDate, endDate, 15000);
}

main();