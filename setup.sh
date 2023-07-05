if [ -z $ZONING_DB_PATH ]
then
    echo 'Must specify $ZONING_DB_PATH'
    kill -INT $$
fi

cat src/schema.sql | sqlite3 $ZONING_DB_PATH
pip3 install -r requirements.txt
