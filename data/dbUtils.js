/*
    Functions for creating and inserting into the sqlite database to store
    posts, comments, and user profiles for running the model
*/

const sqlite = require('sqlite');
const sqlite3 = require('sqlite3');

const fs = require('fs').promises;

async function insertUserProfiles(dbPath, userProfiles){
    const db = await sqlite.open({ filename: `./${dbPath}.db`, driver: sqlite3.Database });

    const createUserProfilesTableQuery = `
        CREATE TABLE IF NOT EXISTS userProfiles (
            username TEXT NOT NULL,
            about TEXT,
            karma INTEGER,
            created TEXT,
            postIDs TEXT,        -- Store JSON array of integers
            commentIDs TEXT,     -- Store JSON array of integers
            favoritePostIDs TEXT,-- Store JSON array of integers
            textSamples TEXT,    -- Store JSON array of strings
            interests TEXT,      -- Store JSON array of strings
            beliefs TEXT,        -- Store JSON array of strings
            PRIMARY KEY (username)
        );
    `;

    await db.run(createUserProfilesTableQuery);

    const insertUserQuery = `
        INSERT OR IGNORE INTO userProfiles (username, about, karma, created, postIDs, commentIDs, favoritePostIDs, textSamples, interests, beliefs)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `

    for(let i = 0; i < userProfiles.length; i++){
        try {
            await db.run(insertUserQuery, [userProfiles[i].username, userProfiles[i].about, userProfiles[i].karma, userProfiles[i].created, JSON.stringify(userProfiles[i].postIDs), JSON.stringify(userProfiles[i].commentIDs), JSON.stringify(userProfiles[i].favoritePostIDs), JSON.stringify(userProfiles[i].textSamples), JSON.stringify(userProfiles[i].interests), JSON.stringify(userProfiles[i].beliefs)]);
        }catch (err){
            console.log(`Error inserting user profiles ${err}`);
        }
    }

    await db.close();

    console.log(`Successfully initialized table and inserted user profiles at ${dbPath}`)

}

async function insertPosts(dbPath, posts){

    const db = await sqlite.open({ filename: `./${dbPath}.db`, driver: sqlite3.Database });


    const createPostsTableQuery = `
        CREATE TABLE IF NOT EXISTS posts   (
            by TEXT ,      -- The user who created the post (string)
            id INTEGER PRIMARY KEY, -- The unique identifier for the post (integer)
            score INTEGER,          -- The score of the post (integer)
            time TEXT,              -- The time the post was created (string)
            title TEXT,             -- The title of the post (string)
            text TEXT,              -- The text content of the post (string)
            url TEXT,               -- The URL related to the post (string)
            urlContent TEXT         -- The content at the URL (string)
        );
    `;

    await db.run(createPostsTableQuery);

    const insertPostsQuery = `
            INSERT OR IGNORE INTO posts (by, id, score, time, title, text, url, urlContent)
            VALUES (?, ?, ?, ?, ?,?,?,?)
    `;

    for(let i = 0; i < posts.length; i++){
        try {
            await db.run(insertPostsQuery, [posts[i].by, posts[i].id, posts[i].score, posts[i].time, posts[i].title, posts[i].text, posts[i].url,posts[i].urlContent ]);
        }catch (err){
            console.log(posts[i]);
            console.log(`Error inserting posts ${err}`);
        }
    }

    await db.close();

    console.log(`Successfully initialized table and inserted posts at ${dbPath}`);

}

async function insertComments(dbPath, comments) {
    const db = await sqlite.open({ filename: `./${dbPath}.db`, driver: sqlite3.Database });

    const createCommentsTableQuery = `
        CREATE TABLE IF NOT EXISTS comments (
            by TEXT,      -- The user who created the post (string)
            id INTEGER PRIMARY KEY, -- The unique identifier for the post (integer)
            time TEXT,              -- The time the post was created (string)
            text TEXT              -- The text content of the post (string)
        );
    `;

    await db.run(createCommentsTableQuery);

    const insertCommentsQuery = `
            INSERT OR IGNORE INTO comments (by, id, time, text)
            VALUES (?, ?, ?, ?)
    `;

    for(let i = 0; i < comments.length; i++){
        try {
            await db.run(insertCommentsQuery, [comments[i].by, comments[i].id, comments[i].time,comments[i].text]);
        }catch (err){
            console.log(`Error inserting comments ${err}`);
        }
    }

    await db.close();

    console.log(`Successfully initialized table and inserted comments at ${dbPath}`);

}


async function initializeDB(dbPath){
    const db = await sqlite.open({ filename: `./${dbPath}.db`, driver: sqlite3.Database });

    console.log('Database created successfully!');
    
    // Close the database connection
    await db.close();
}

/*
    Merge the contents of two databases, and 
    rename the resulting database to a final name.

    (all chatgpt and it works, i don't want to fuck with it)
*/
async function mergeDatabases(leftDBPath, rightDBPath, finalDBPath){
    const leftDB = await sqlite.open({filename: leftDBPath, driver: sqlite3.Database});
    const rightDB = await sqlite.open({filename: rightDBPath, driver: sqlite3.Database});

    await leftDB.exec("BEGIN TRANSACTION");
    const tables = await rightDB.all("SELECT name FROM sqlite_master WHERE type='table'");

    console.log(`Merging databases ${leftDBPath} and ${rightDBPath} into ${finalDBPath}...`);

    for (const table of tables) {
        const tableName = table.name;
        console.log(`Merging table: ${tableName}`);
  
        // Get the rows from tables in the right database
        const rows = await rightDB.all(`SELECT * FROM ${tableName}`);
  
        //chatgpt
        if (rows.length > 0) {
            for (const row of rows) {
                // Build the insert SQL statement dynamically based on the row
                const columns = Object.keys(row).join(',');
                const placeholders = Object.keys(row).map(() => '?').join(',');
                const values = Object.values(row);
    
                // Insert the data into the right database, using INSERT OR IGNORE to avoid duplicate primary keys
                const insertSQL = `INSERT OR IGNORE INTO ${tableName} (${columns}) VALUES (${placeholders})`;

                await leftDB.run(insertSQL, values);
            }
        }
    }

    await leftDB.exec('COMMIT');

    await leftDB.close();
    await rightDB.close();

    //move the merged left database to the final db path, and remove the right database
    await fs.rename(leftDBPath, finalDBPath);
    await fs.unlink(rightDBPath);
}

/*
async function main(){
    //await initializeDB("test4");
    //await initializeDB("test5");
    
    await insertComments("test4", [{id: 1, time: '1', text: '1', by: '1'}, {id: 2, time: '1', text: '1', by: '1'}]);
    await insertComments("test5", [{id: 1, time: '1', text: '1', by: '2'}, {id: 3, time: '1', text: '1', by: '1'}]);
    await insertUserProfiles("test4", [{username: "test", about: "testabout1", karma: 2, commentIDs: [], favoritePostIDs: [],textSamples: [], interests: [], beliefs: []}, {username: "test2", about: "testabout", karma: 2, commentIDs: [], favoritePostIDs: [],textSamples: [], interests: [], beliefs: []}])
    await insertUserProfiles("test5", [{username: "test", about: "testabout2", karma: 2, commentIDs: [], favoritePostIDs: [],textSamples: [], interests: [], beliefs: []}, {username: "test3", about: "testabout", karma: 2, commentIDs: [], favoritePostIDs: [],textSamples: [], interests: [], beliefs: []}])
    await insertPosts("test4", [{id: 1, time: '111', text: '1', by: '1', title: '1', score: 2, url: '1', urlContent: '1'}, {id: 2, time: '111', text: '1', by: '1', title: '1', score: 2, url: '1', urlContent: '1'}]);
    await insertPosts("test5", [{id: 1, time: '222', text: '1', by: '1', title: '1', score: 2, url: '1', urlContent: '1'}, {id: 3, time: '111', text: '1', by: '1', title: '1', score: 2, url: '1', urlContent: '1'}])
    

    await mergeDatabases("./test4.db", "./test5.db", "./test6.db");
    

}

main();
*/

module.exports = {
    initializeDB,
    insertUserProfiles,
    insertPosts,
    insertComments,
    mergeDatabases
}