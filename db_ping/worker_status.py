import mariadb

from datetime import timedelta

from pprint import pprint
import inspect


def run(conn, control, counters):

    cur = conn.cursor()

    """
    SHOW STATUS LIKE "uptime"


    SET profiling=1;
    SELECT xyz
    SHOW PROFILE;
    SET profiling=0;
    """

    #pprint(inspect.getmembers(cur))
    """
     ('statement', 'SELECT host,user FROM user'),
     ('warnings', 0)
    """

    try:
        cur.execute("SHOW STATUS LIKE 'uptime'")
    except mariadb.Error as e:
        print(f"Error: {e}")
    else:
        if not control['config']['quiet']:
            uptime = timedelta(seconds=int(cur.fetchone()[1]))
            print(f'Uptime: {uptime}')

    try:
        cur.execute(
            "SELECT host FROM information_schema.processlist WHERE id=?",
            (conn.connection_id,),
        )
    except mariadb.Error as e:
        print(f"Error: {e}")
    else:
        if not control['config']['quiet']:
            client_connection = cur.fetchone()[0]
            print(f'Client connection: {client_connection}')

    try:
        cur.execute("SHOW VARIABLES LIKE 'hostname'")
    except mariadb.Error as e:
        print(f"Error: {e}")
    else:
        if not control['config']['quiet']:
            server_hostname = cur.fetchone()[1]
            print(f'Server hostname: {server_hostname}')

    try:
        cur.execute("SHOW VARIABLES LIKE 'max_connections'")
    except mariadb.Error as e:
        print(f"Error: {e}")
    else:
        if not control['config']['quiet']:
            max_connections = cur.fetchone()[1]
            print(f'Max connections: {max_connections}')

    # Parsing the 'SHOW PROCESSLIST' would probable be more useful
    try:
        cur.execute("SHOW STATUS LIKE 'threads_connected'")
    except mariadb.Error as e:
        print(f"Error: {e}")
    else:
        if not control['config']['quiet']:
            threads_connected = cur.fetchone()[1]
            print(f'Connections open at server: {threads_connected}')

    # Free resources
    cur.close()
