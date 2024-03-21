## Setup

1. Ensure you have the necessary dependencies:

- Python3+
- Sqlite3 (`sudo apt install sqlite3`)
- Java (`sudo apt install openjdk-11-jre-headless`)

2. Define a filepath for the database

```
export ZONING_DB_PATH=$(pwd)/zoning.db
```

3. Run `setup.sh`

4. Run `src/main.py`

This will generate an HTML file which can be sent out via e-mail.
