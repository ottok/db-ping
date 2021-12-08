import mariadb
import time
from contextlib import closing

def run(conn, control, counters):
    with closing(conn):
        while control['run']:

                start = time.time()
                try:
                    conn.ping()
                except mariadb.Error as e:
                    print(
                        'Ping failed after {} seconds with error: {}'.format(
                            round(time.time() - start, 2),
                            e,
                        )
                    )
                else:
                    if counters['ping']['id'] != conn.connection_id:
                        counters['ping']['id'] = conn.connection_id
                        counters['ping']['connects'] += 1

                # Always update time
                counters['ping']['time'] = time.time() - start

                # Increment counter
                counters['ping']['seq'] += 1

                # Sleep must be accurately one second if the query was less than a
                # second. If the query was over a second, the SLA as tracked by this
                # tool is breached and sleeping a full second is correct behaviour.
                if counters['write']['time'] < 1:
                    time.sleep(1-counters['write']['time'])
