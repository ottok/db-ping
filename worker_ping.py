import mariadb
import time

def run(conn, control, counters):
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

        # Ensure increment never exceeds main counter, otherwise SLA cals will
        # be over 100%
        if counters['ping']['seq'] <= counters['seq']:
            counters['ping']['seq'] += 1

        time.sleep(1)

    print('Ping ended')

    # Free resources
    conn.close()
