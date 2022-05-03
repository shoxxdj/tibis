import yaml
import sqlite3
import tibis.lib.args_parser as args_parser
import tibis.lib.logger as log
import tibis.lib.static as static
from pathlib import Path

def main():
    path=Path(static.tibis_full_config_location)
    if(not path.is_file()):
        log.info("Create config file")
        path=Path(static.tibis_config_location)
        path.mkdir(parents=True,exist_ok=True)
        log.success("Done")

        log.info("Create key directory")
        path=Path(static.tibis_keys_location)
        path.mkdir(parents=True,exist_ok=True)
        log.success("Done")

        log.info("Create storage directory")
        path=Path(static.tibis_storage_path)
        path.mkdir(parents=True,exist_ok=True)
        log.success("Done")

        with open(static.tibis_full_config_location,'w') as file:
            yaml.dump(static.default_config,file)

    #log.info("Setup database if not exists")
    conn=None
    try:
        conn=sqlite3.connect(static.tibis_db_location)
        cursor_obj = conn.cursor()
        table = static.tibis_database_init;
        cursor_obj.execute(table)
    except sqlite3.Error as e:
        raise e
    finally:
        if conn:
            conn.close()


    args_parser.args_parser()

if __name__ == "__main__":
 main()
