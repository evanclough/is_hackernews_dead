/*

    Functions for creating and inserting into the sqlite database to store
    posts, comments, and user profiles for running the model

*/

const sqlite = require('sqlite');
const sqlite3 = require('sqlite3');

const fs = require('fs').promises;

/*
    Insert a list of user profiles into the database.
*/
async function insertUserProfiles(dbPath, userProfiles){
    const db = await sqlite.open({ filename: `./${dbPath}.db`, driver: sqlite3.Database });

    const createUserProfilesTableQuery = `
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            about TEXT,
            karma INTEGER,
            created INTEGER,
            user_class TEXT,
            post_ids TEXT,
            comment_ids TEXT,
            favorite_post_ids TEXT
        );
    `;

    await db.run(createUserProfilesTableQuery);

    const insertUserQuery = `
        INSERT OR IGNORE INTO users (username, about, karma, created, user_class, post_ids, comment_ids, favorite_post_ids)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `;

    for(let i = 0; i < userProfiles.length; i++){
        try {
            await db.run(insertUserQuery, [userProfiles[i].username, userProfiles[i].about, userProfiles[i].karma, userProfiles[i].created, "real", JSON.stringify(userProfiles[i].postIDs), JSON.stringify(userProfiles[i].commentIDs), JSON.stringify(userProfiles[i].favoritePostIDs)]);
        }catch (err){
            console.log(`Error inserting user profiles ${err}`);
        }
    }

    await db.close();

    console.log(`Successfully initialized table and inserted user profiles at ${dbPath}`);
}

/*
    Insert a list of posts into the database.
*/
async function insertPosts(dbPath, posts){

    const db = await sqlite.open({ filename: `./${dbPath}.db`, driver: sqlite3.Database });

    const createPostsTableQuery = `
        CREATE TABLE IF NOT EXISTS posts   (
            by TEXT,
            id INTEGER PRIMARY KEY,
            score INTEGER,
            time INTEGER,
            title TEXT,
            text TEXT,
            url TEXT,
            url_content TEXT
        );
    `;

    await db.run(createPostsTableQuery);

    const insertPostsQuery = `
            INSERT OR IGNORE INTO posts (by, id, score, time, title, text, url, url_content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `;

    for(let i = 0; i < posts.length; i++){
        try {
            await db.run(insertPostsQuery, [posts[i].by, posts[i].id, posts[i].score, posts[i].time, posts[i].title, posts[i].text, posts[i].url, posts[i].urlContent]);
        }catch (err){
            console.log(posts[i]);
            console.log(`Error inserting posts ${err}`);
        }
    }

    await db.close();

    console.log(`Successfully initialized table and inserted posts at ${dbPath}`);
}

/*
    Insert a list of comments into the database.
*/
async function insertComments(dbPath, comments) {
    const db = await sqlite.open({ filename: `./${dbPath}.db`, driver: sqlite3.Database });

    const createCommentsTableQuery = `
        CREATE TABLE IF NOT EXISTS comments (
            by TEXT,
            id INTEGER PRIMARY KEY,
            time INTEGER,
            text TEXT,
            parent INTEGER
        );
    `;

    await db.run(createCommentsTableQuery);

    const insertCommentsQuery = `
            INSERT OR IGNORE INTO comments (by, id, time, text, parent)
            VALUES (?, ?, ?, ?, ?)
    `;

    for(let i = 0; i < comments.length; i++){
        try {
            await db.run(insertCommentsQuery, [comments[i].by, comments[i].id, comments[i].time, comments[i].text, comments[i].parent]);
        }catch (err){
            console.log(`Error inserting comments ${err}`);
        }
    }

    await db.close();

    console.log(`Successfully initialized table and inserted comments at ${dbPath}`);
}

/*
    Initialize the sqlite database.
*/
async function initializeDB(dbPath){
    const db = await sqlite.open({ filename: `./${dbPath}.db`, driver: sqlite3.Database });

    console.log(`Successfully created database at ./${dbPath}.db`);
    
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

module.exports = {
    initializeDB,
    insertUserProfiles,
    insertPosts,
    insertComments,
    mergeDatabases
}