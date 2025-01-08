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
  const currentStartDate = {
    year: 2023,
    month: 8, 
    day: 14
  };

  const currentEndDate = {
    year: 2024, 
    month: 12,
    day: 31
  };

  grabDateRangeFPRawHTML(currentStartDate, currentEndDate, 15000);
}

main();