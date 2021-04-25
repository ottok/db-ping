import mariadb
import time

from pprint import pprint


def run(conn, control, counters):
    cur = conn.cursor()
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
                counters['read']['processlist_count'] = row[0]

            if counters['read']['id'] != conn.connection_id:
                counters['read']['id'] = conn.connection_id
                counters['read']['connects'] += 1

        # Always update time
        counters['read']['time'] = time.time() - start

        # Ensure increment never exceeds main counter, otherwise SLA cals will
        # be over 100%
        if counters['read']['seq'] <= counters['seq']:
            counters['read']['seq'] += 1


        time.sleep(1)

    print('Reader ended')

    # Free resources
    cur.close()
    conn.close()
