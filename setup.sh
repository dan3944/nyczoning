export ZONING_DB_PATH=database.db

if [ ! -f $ZONING_DB_PATH ]
then
    echo "creating $ZONING_DB_PATH"
    cat db/schema.sql | sqlite3 $ZONING_DB_PATH
fi

source bin/activate
pip install -r requirements.txt
