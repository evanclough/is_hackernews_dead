/*

    Various functions used across the different scripts used to 
    retrieve and parse Hacker News data for the experiment.

*/

const fs = require('fs').promises;
const path = require('path');

const axios = require('axios');
const cheerio = require('cheerio');


/*

    Read in the raw string contents of a given file path.

*/
async function readFile(filePath){
    try {
        // Read the file content asynchronously 
        const data = await fs.readFile(filePath, 'utf8');
        return data;
    } catch (err) {
        console.error('Error reading file:', err);
    }
}


/*

    Read in a JSON file from a given file path.

*/
async function readJsonFile(filePath) {
    const data = await readFile(filePath);
    const jsonData = JSON.parse(data);
    return jsonData;
}

/*

    Writes a string to a given file path.

*/
async function writeStringToFile(string, filePath) {
    try {
      await fs.writeFile(filePath, string, 'utf8');
      console.log(`Successfully wrote to ${filePath}.`);
    } catch (err) {
      console.error(`Error writing to ${filePath}`, err);
    }
}

/*

    Writes a given json file to a given file path.

*/
async function writeJsonToFile(jsonData, filePath) {
    const jsonString = JSON.stringify(jsonData, null, 2);  
    await writeStringToFile(jsonString, filePath);
}

/*

    Create a directory at a given path.
    
*/
async function createDirectory(path) {
    try {
        await fs.mkdir(path, { recursive: true });
        console.log(`Successfully created directory at path ${path}`);
    } catch (err) {
        console.error(`Error creating directory at path ${path}:`, err);
    }
}

/*

    Return the names of all files in a given directory.

*/

async function getFiles(directoryPath) {
    try {
      const files = await fs.readdir(directoryPath);
      const onlyFiles = [];
      
      for (const file of files) {
        const filePath = path.join(directoryPath, file);
        const stats = await fs.stat(filePath);
        if (stats.isFile()) {
          onlyFiles.push(file);
        }
      }
  
      return onlyFiles;
    } catch (err) {
      console.error('Error reading directory:', err);
      return [];
    }
}

/*

    Return the names of all directories in a given directory.

*/

async function getDirectories(directoryPath) {
    try {
      const files = await fs.readdir(directoryPath);
      const onlyDirectories = [];
      
      for (const file of files) {
        const filePath = path.join(directoryPath, file);
        const stats = await fs.stat(filePath);
        if (!stats.isFile()) {
          onlyDirectories.push(file);
        }
      }
  
      return onlyDirectories;
    } catch (err) {
      console.error('Error reading directory:', err);
      return [];
    }
}


/*

    Check whether or not a given file exists.

*/
async function checkFileIfExists(filePath) {
    try {
      await fs.access(filePath);
      return true;
    } catch (error) {
      return false;
    }
}


/*
    Returns a list of date objects in a given range.
    (There's probably a preset function to do this)
*/

function getDateRange(startDate, endDate){
    //chcek input
    if (startDate.year == undefined || startDate.month == undefined || startDate.day == undefined){
      throw "ill formed start date in getDateRange";
    }
    if (endDate.year == undefined || endDate.month == undefined || endDate.day == undefined){
      throw "ill formed end date in getDateRange";
    }
    if(startDate.year < 2010 || startDate.year > 2024){
      throw `out of range year in start date in getDateRange ${startDate.year}`;
    }
    if(endDate.year < 2010 || endDate.year > 2024){
      throw `out of range year in end date in getDateRange ${endDate.year}`;
    }
    if (startDate.month < 0 || startDate.month > 12){
      throw `out of range month in start date in getDateRange ${startDate.month}`;
    }
    if (endDate.month < 0 || endDate.month > 12){
      throw `out of range month in end date in getDateRange ${startDate.month}`;
    }
    if (startDate.day < 0 || startDate.day > 31){
      throw `out of range day in start date in getDateRange ${startDate.month}`;
    }
    if (endDate.day < 0 || endDate.day > 31){
      throw `out of range day in end date in getDateRange ${startDate.month}`;
    }
  
    const currentDate = {
      year: startDate.year,
      month: startDate.month,
      day: startDate.day
    };

    const dateRange = [{...currentDate}];
  
    const monthEnds = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    const leapYearMonthEnds = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  
    while (!(currentDate.year == endDate.year && currentDate.month == endDate.month && currentDate.day == endDate.day)){  
        const currentMonthEnds = currentDate.year % 4 != 0 ? monthEnds : leapYearMonthEnds;
    
        const iterateMonth = currentDate.day == currentMonthEnds[currentDate.month - 1];
        const iterateYear = iterateMonth && currentDate.month == 12;
    
        currentDate.year =  currentDate.year + (iterateYear ? 1 : 0);
        currentDate.month = iterateYear ? 1 : currentDate.month + (iterateMonth ? 1 : 0);
        currentDate.day = (iterateMonth || iterateYear) ? 1 : currentDate.day + 1;
        dateRange.push({
            year: currentDate.year,
            month: currentDate.month,
            day: currentDate.day
        });
    }
    
    return dateRange;
}


/*

    Given a date object, returns a string formatted
    in the way Hacker News does it.

*/
function getDateString(date){
    return `${date.year}-${date.month}-${date.day}`;
}

/*
    Given a start and end date, return a string
    containing both.
*/

function getDateRangeString(startDate, endDate){
    const startDateString = getDateString(startDate);
    const endDateString = getDateString(endDate);
    return `${startDateString}to${endDateString}`;
}

/*

    Sleep for a given time period, 
    used in adding intervals between API calls.

*/
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/*
    Runs a get request on the given URL.

    (Currently trying cheerio for only getting useful info).
*/

async function grabLinkContent(url){
    const response = await axios.get(url, {timeout: 3000});
    const cheerioData = cheerio.load(response.data);
    const content = cheerioData('body').text();

    return content;
}

/*
    Filter out duplicate atoms from an array.
*/
function removeDuplicateAtoms(array){
    return array.filter((x, i) => array.slice(i + 1).filter(y => x === y).length == 0);
}


/*
    Filter out duplicate objects from an array, given a key sequence.
*/
function removeDuplicateObjectsByKeySeq(array, keySeq){
    return array.filter((x, i) => {
        const xValue = keySeq.reduce((acc, key) => acc[key], x);
        if(xValue === undefined){
            throw `Error in attempting to remove duplicate objects from an array given keySeq ${keySeq}: key is not present in object ${JSON.stringify(x)} at index ${i}`;
        } else {
            return array.slice(i + 1).filter(y => {
                const yValue = keySeq.reduce((acc, key) => acc[key], y);
                return xValue === yValue;
            }).length == 0;
        }
    });
}

/*

    Scrape all post IDs from a Hacker News HTML page containing a list of posts,
    used in getting post IDs from front pages, and favorites pages.

*/
function scrapePostIDsFromHNPage(htmlString, name){
    //use this regex to pull a list of post IDs from the raw HTML
    const itemIDRegex = /item\?id=(\d+)/g;
    const itemIDMatches = htmlString.match(itemIDRegex);
    //if the returned list from the regex match is null, something is wrong    
    if (itemIDMatches != null){
        //first filter to only catch uniques
        const idStrings = itemIDMatches.filter((item, index) => index == 0 ? true : itemIDMatches[index - 1] != item);
        
        //pull out id with another regex
        const numRegex = /(\d+)/;
        const postIDs = idStrings.map(idString => {
            const idFirst = idString.search(numRegex);
            //if it's -1, someting is wrong, indicate and filter out later
            if (idFirst == -1){
                console.log(`Error in parsing post IDs from Hacker News HTML of name ${name}`);
                return '-1';
            }else {
                return idString.slice(idFirst);
            }
        });

        const filteredPostIDs = postIDs.filter(postID => postID != '-1').map(postID => parseInt(postID));
        return filteredPostIDs;
    }else {
        throw `Error in parsing post IDs from Hacker News HTML of name ${name}`
    }
}

/*

Select N random elements from a given array (with potential duplicates)

*/
function selectNRandomElements(array, N){
    if (array.length === 0){
        throw "Error: cannot select random elements from empty array";
    }
    return [...Array(N)].map(a => array[Math.floor(Math.random() * array.length)]);
}

module.exports = {
    readFile, 
    readJsonFile, 
    writeStringToFile,
    writeJsonToFile,
    createDirectory,
    getDateRange,
    getDateString,
    getDateRangeString,
    sleep,
    grabLinkContent,
    removeDuplicateAtoms,
    removeDuplicateObjectsByKeySeq,
    scrapePostIDsFromHNPage,
    selectNRandomElements,
    getFiles,
    getDirectories,
    checkFileIfExists
}