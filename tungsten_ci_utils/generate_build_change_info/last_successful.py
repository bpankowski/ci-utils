import sys
import argparse
import MySQLdb
import logging
import json

log = logging.getLogger(__name__)

def set_logging():
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    log.addHandler(console)

set_logging()

def get_json_data(file):
    json_file = open(file).read()
    data = json.loads(json_file)
    return data

def close_db_exit_err(db):
    if db is not None:
        db.close()
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials-json", action="append")
    parser.add_argument("branch")
    parser.add_argument("build_number")
    args = parser.parse_args()
    branch = str(args.branch)
    credentials_json = args.credentials_json[0]

    build_number = og_build_number = int(args.build_number)
    build_number -= 1

    db_config = get_json_data(credentials_json)

    try:
        db = MySQLdb.connect(
            user=db_config["user"],
            passwd=db_config["passwd"],
            db=db_config["db"],
            host=db_config["host"],
            port=db_config["port"]
        )
        cur = db.cursor()
        log.debug('connected to db')
    except:
        log.error('database connection error')
        sys.exit(1)

    while build_number > 0:
        query = """
        SELECT result FROM zuul_buildset WHERE id IN 
        (SELECT buildset_id FROM zuul_build WHERE log_url LIKE CONCAT('%%periodic-nightly%%/', %s, '/%s%%'))
        """

        log.debug('checking if buildset %s was successful', build_number)

        try:
            cur.execute(query, (branch, build_number))
            result = list(cur)
        except:
            log.error('Query execution error')
            close_db_exit_err(db)

        if len(result) > 0:
            if result[0][0] == 'SUCCESS':
                last_successful = build_number
                log.debug('last successful buildset before %s found, number: %s', og_build_number, last_successful)
                print(last_successful)
                break
            elif result[0][0] == 'FAILURE':
                log.debug('buildset %s was a failure', build_number)
            else:
                log.warning('unknown buildset result for current iteration (build number %s)', build_number)
        else:
            log.error('buildset number %s not found in the database, aborting', build_number)
            close_db_exit_err(db) # we exit here, assuming there are no gaps in (incremental) build numbers

        build_number -= 1

    else:
        log.error('last successful buildset not found')
        close_db_exit_err(db)

    db.close()

if __name__ == '__main__':
    main()