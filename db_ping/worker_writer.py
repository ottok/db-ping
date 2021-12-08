import mariadb
import time
from contextlib import closing

from pprint import pprint


def run(conn, control, counters):
    with closing(conn), closing(conn.cursor()) as cur:
        while control['run']:

            start = time.time()
            try:
                cur.execute("SELECT count(*) FROM information_schema.processlist")
            except mariadb.Error as e:
                print(
                    'Failed after {} seconds with error: {}'.format(
                        round(time.time() - start, 2), e
                    )
                )
            else:
                # print(
                #     'Succeeded in {} seconds (connection id: {})'.format(
                #         round(time.time() - start, 2),
                #         conn.connection_id
                #     )
                # )
                for row in cur:
                    # print(
                    #     'Succeeded in {} seconds (connection id: {})'.format(
                    #         round(time.time() - start, 2),
                    #         conn.connection_id
                    #     )
                    # )
                    counters['write']['processlist_count'] = row[0]

                if counters['write']['id'] != conn.connection_id:
                    counters['write']['id'] = conn.connection_id
                    counters['write']['connects'] += 1

            # Always update time
            counters['write']['time'] = time.time() - start

            # Increment counter
            counters['write']['seq'] += 1

            # Sleep must be accurately one second if the query was less than a
            # second. If the query was over a second, the SLA as tracked by this
            # tool is breached and sleeping a full second is correct behaviour.
            if counters['write']['time'] < 1:
                time.sleep(1-counters['write']['time'])
