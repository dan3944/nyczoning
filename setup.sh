if [ -z $ZONING_DB_PATH ]
then
    echo 'Must specify $ZONING_DB_PATH'
    kill -INT $$
fi

if [ ! -f $ZONING_DB_PATH ]
then
    echo "creating $ZONING_DB_PATH"
    cat src/schema.sql | sqlite3 $ZONING_DB_PATH
fi

python -m venv .
source bin/activate
pip install -r requirements.txt
