CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY,
    datetime TEXT NOT NULL UNIQUE,
    pdf_filename TEXT UNIQUE,
    pdf_url TEXT,
    notified BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    meeting_id INTEGER NOT NULL,
    ulurp_number TEXT,
    description TEXT,
    location TEXT,
    FOREIGN KEY(meeting_id) REFERENCES meeting(meeting_id)
)
