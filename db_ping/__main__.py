#!/usr/bin/python3
"""
MariaDB/MySQL compatible database connection and capability checker

This tool helps to quickly identify database connectivity issues such as:
- DNS propagation delay, hostname not matching active database server
- TCP/IP routing issues, server not reachable
- TLS certificate issues
- Authentication errors
- Server load issues: too many connections, too many queries or too much load
- Server health issues: disk write operations stalled or other I/O delay

Example invocation and output:
    $ db-ping --host database-1.example.com --user dbuser --password abc123 appdb
    Connecting dbuser@database-1.example.com:3306...
    Executed 1 DELETE in 0.01 ms, 1 INSERT in 0.12 ms, 1 UPDATE in 0.1 ms, 1 SELECT in 0.01 ms
    Executed 1 DELETE in 0.01 ms, 1 INSERT in 0.12 ms, 1 UPDATE in 0.1 ms, 1 SELECT in 0.01 ms
    Executed 1 DELETE in 0.01 ms, 1 INSERT in 0.12 ms, 1 UPDATE in 0.1 ms, 1 SELECT in 0.01 ms
    ^C
    --- database-1.example.com db-ping statistics ---
    3 DELETE in 0.2 ms (min/avg/max 0.01/0.01/0.01)
    3 INSERT in 0.36 ms (min/avg/max 0.12/0.12/0.12)
    3 UPDATE in 0.2 ms (min/avg/max 0.01/0.01/0.01)
    1 SELECT in 0.03 ms (min/avg/max 0.03/0.03/0.03)
    SQL execution time: 0.79 ms
    Wall clock duration: 3.02 seconds
    Connection errors/connects: 0
    Availability: 100.00%

Database server, name and user credentials can be given as command-line
parameters or they are read from environment variables DB_* or from .my.cnf
config files.

Database hostname and user password don't have any defaults, they must be given.
Default username and database is 'db-ping'. The database will be used to create
a small table 'db-ping' which will have random values written and read in order
to verify that the database server accepts both reads and writes, and for example
the filesystem is not stuck. If no database name is given, db-ping will attempt
to create the table inside the 'tmp' or 'test' database, if such exists.

It is recommended to use the application credentials when running db-ping to
verify that everything would work just as the application would see it. The
test table is safely created also inside a production database, as it will always
be a separate table that nobody else uses, called 'db-ping'.
"""

import argparse
import configparser
import copy
import dns.resolver
import mariadb
import sys
import os
import re
import socket
import time
import threading

from . import worker_status
from . import worker_reader
from . import worker_writer
from . import worker_ping

from pprint import pprint
import inspect


def new_connection(config):
    #pprint(dir(mariadb))
    #pprint(inspect.getmembers(mariadb))
    conn = mariadb.connect(
        user=config['user'],
        password=config['password'],
        host=config['host'],
        port=config['port'],
        database=config['database'],
        connect_timeout=10,
        read_timeout=10,
        write_timeout=10,
        ssl=True,  # Force TLS protection
        ssl_verify_cert=not config['insecure'],  # Prevent man-in-the-middle attacks
        ssl_ca=config['ca_cert'],
    )
    # https://mariadb-corporation.github.io/mariadb-connector-python/connection.html#auto_reconnect
    conn.auto_reconnect = True;
    return conn


def print_status(start, now, previous):
    if now['ping']['seq'] == previous['ping']['seq']:
        # Ping taking longer than 1 second, show time as zero
        now['ping']['time'] = 0

    if now['ping']['id'] != previous['ping']['id'] or \
       now['read']['id'] != previous['read']['id']:
        print('Database client reconnected')

    print(
        '{}#{} {}s (connects: {}/4)'.format(
            round(time.time()-start),
            now['seq'],
            round(now['ping']['time'], 2),
            1 + now['ping']['connects'] + now['read']['connects'] + now['write']['connects'],
        )
    )
    #print('Counters: {} {} {} {}'.format(
    #    now['seq'],
    #    now['ping']['seq'],
    #    now['read']['seq'],
    #    now['write']['seq'],
    #))

    # Increment counter on every printed line
    now['seq'] += 1


def print_summary(config, start, now, previous):
    print(f'--- database server {config["host"]} summary ---')
    print('Wall clock duration:', round(time.time() - start), 'seconds')
    print('# Total:', now['seq'])
    print('# Pings:', now['ping']['seq'], '(SLA:', 100*(now['ping']['seq']/now['seq']), '%)')
    print('# Reads:', now['read']['seq'], '(SLA:', 100*(now['read']['seq']/now['seq']), '%)')
    print('# Writes:', now['write']['seq'], '(SLA:', 100*(now['write']['seq']/now['seq']), '%)')


# As config names are not identical to their expected environment variable
# names, create a map of them
configEnvMap = {
    'host': 'DB_HOST',
    'port': 'DB_PORT',
    'user': 'DB_USER',
    'password': 'DB_PASSWORD',
    'database': 'DB_NAME',
}


def main(args=None):
    global configEnvMap

    # Configuration parameters, some with default values
    config = {
        'quiet': False,
        'host': '',  # No default host, assume db-ping runners always wants to define host
        'port': 3306,
        'user': 'db-ping',
        'password': '',
        'database': '',
        'ca_cert': None,  # Python argparse converts dashes to undescores
        'insecure': False,
    }

    configFromEnvironmentVariables = []
    configFromConfigFiles = []

    # Read a my.cnf if exists
    # Note that file must have some kind of [section], otherwise ConfigParser will
    # fail with "configparser.MissingSectionHeaderError: File contains no section headers."
    # See https://bugs.python.org/issue22253 and https://github.com/python/cpython/pull/2735
    mycnf = configparser.ConfigParser(strict=False)
    mycnf.read(['.my.cnf', os.path.expanduser('~/.my.cnf')])

    # An alternative source would be to run 'mariadb --print-defaults' and read the
    # values it returned. This would evaluate the [client], [mariadb-client] etc
    # sections in correct order.

    # ArgumentParser shows help texts automatically based on Python docstring
    # (the comment at the top of the file)
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.strip().split('\n', maxsplit=1)[0],
        epilog=__doc__.strip().split('\n', maxsplit=1)[1],
    )
    parser.add_argument('--host', help='Database server hostname or IP address')
    parser.add_argument('--port', type=int, help='Database server port')
    parser.add_argument('--user', help='Database username')
    parser.add_argument('--password', help='Database user password')
    parser.add_argument('--database', help='Database name')
    x = parser.add_mutually_exclusive_group()
    x.add_argument('--insecure', help="Don't verify TLS certificates", action='store_true')
    x.add_argument('--ca-cert', help='Path to custom CA pem file, needed if using self-signed TLS certificates')
    parser.add_argument('--quiet', help='Be less ', action='store_true')
    args = parser.parse_args()

    # Override default config values with:
    # 1. Values from command-line arguments
    # 2. Values from environment variables
    # 3. Values from my.cnf
    # 4. Values from my.cnf with dash instead of underscore
    for key in config:
        if key in args and getattr(args, key) != None:
            config[key] = getattr(args, key)
        elif key in configEnvMap.keys() and configEnvMap[key] in os.environ and os.environ[configEnvMap[key]]:
            config[key] = os.environ[configEnvMap[key]]
            configFromEnvironmentVariables.append(configEnvMap[key])
        elif 'client' in mycnf.sections() and mycnf.has_option('client', key):
            config[key] = mycnf.get('client', key)
            configFromConfigFiles.append(key)
        elif 'client' in mycnf.sections() and mycnf.has_option('client', key.replace('_', '-')):
            config[key] = mycnf.get('client', key.replace('_', '-'))
            configFromConfigFiles.append(key)

    # Check that there is a value for each field
    if len(config['host']) == 0:
        print('Error: No host defined')
        print('Run "db-ping --help" for more information.')
        sys.exit(1)

    if not config['quiet'] and len(configFromEnvironmentVariables) > 0:
        print('Using envs:', ', '.join(configFromEnvironmentVariables))

    if not config['quiet'] and len(configFromConfigFiles) > 0:
        print('Using .my.cnf:', ', '.join(configFromConfigFiles))

    print(
        'Connecting {}@{}:{}...'.format(
            config['user'],
            config['host'],
            config['port'],
        )
    )

    # Measure total wall clock time for execution
    start = time.time()

    try:
        conn = new_connection(config)
    except mariadb.OperationalError as e:
        # E.g. unknown host
        print(f'Error: Unable to connect: {e}')
        sys.exit(1)
    except mariadb.Error as e:
        print(f'Error: Connection failed: {e}')
        connection_time = round(time.time() - connect_start, 1)
        if round(connection_time) == 10:
            print('Error: Timeout after 10 seconds')
        else:
            print(f'Connection closed after {connection_time} seconds')
        sys.exit(1)
    except Exception as e:
        # E.g. unknown host
        print(f'Error: {e}')
        sys.exit(1)

    # Check if host starts like an IPv4 or IPv6 address
    if re.search('(^[0-9]{1,3}\.)|(^[0-9a-fA-F]{1,4}:)', config['host']):
        # Show what name IP resolves to
        addr_info = socket.gethostbyaddr(config['host'])[0]
    else:
        # Show what IP name resolves to
        # Define type=6 to only get each IP only once in result set
        addrinfo = socket.getaddrinfo(config['host'], config['port'], 0, 6)
        ip_list = list()
        for addr in addrinfo:
            ip_list.append(addr[4][0])
        addr_info = ', '.join(ip_list)

        dns_response = dns.resolver.query(config['host'])
        dns_expiry = round(dns_response.expiration - time.time())
        # @TODO: Check if record has DNSSEC signature yes/no
        # @TODO: Check if DNSSEC signature is valid/invalid

    print(f'Successfully connected to {conn.server_name} ({addr_info})')

    if dns_response:
        print(f'Hostname resolves to {dns_response.canonical_name.to_text()}')
        print(f'DNS record expires in {dns_expiry} seconds')

    #pprint(dir(conn))
    #pprint(inspect.getmembers(conn))

    server_debug = [
        'server_port',
        'user',
        'database',
        'tls_cipher',
        'tls_version',
        'server_info',
        'server_version_info',
        'character_set',
        'collation',
        'dsn',
        'warnings',
        'connection_id',
    #    'auto_reconnect',
    ]

    if not config['quiet']:
        for i in server_debug:
            print(' ', i + ':', getattr(conn, i))

    # Run multiple parallel threads to prevent connections or printing of results
    # stalling because of any single timeout or network I/O or remote disk I/O issue
    threads = list()

    # Flag to tell other threads we'd like to stop
    control = {
        'config': config,
        'run': True
    }

    # Shared counters
    # Prevent race conditions by ensuring each thread only writes to a branch of
    # the dict that nobody else writes to. Summarize all stats in main thread code.
    counters = {
        'ping': {
            'id': 0,  # connection id
            'connects': 0,
            'seq': 0,  # sequence number, always increments by one
            'time': 0.0,  # time logged for latest
        },
        'read': {
            'id': 0,
            'connects': 0,
            'seq': 0,
            'time': 0.0,
        },
        'write': {
            'id': 0,
            'connects': 0,
            'seq': 0,
            'time': 0.0,
        },
        'seq': 1,  # Start top-level print counter at 1
    }

    # Copy of previous values
    old_counters = copy.deepcopy(counters)

    try:
        # Add thread for general database information and printer
        threads.append(
            threading.Thread(
                target=worker_status.run,
                kwargs={'conn': conn, 'control': control, 'counters': counters}
            )
        )

        # Add thread for database client ping
        threads.append(
            threading.Thread(
                target=worker_ping.run,
                kwargs={'conn': new_connection(config), 'control': control, 'counters': counters}
            )
        )

        # Add thread for database reader
        threads.append(
            threading.Thread(
                target=worker_reader.run,
                kwargs={'conn': new_connection(config), 'control': control, 'counters': counters}
            )
        )

        # Add thread for database writer
        threads.append(
            threading.Thread(
                target=worker_writer.run,
                kwargs={'conn': new_connection(config), 'control': control, 'counters': counters}
            )
        )


        # Start all threads
        for i in range(0, len(threads)):
            threads[i].start()

        # Reset total wall clock here to ensure it starts from zero as the threads do
        start = time.time()

        while control['run']:
            # Tick every second, always show steady wall time. If a child thread is
            # too slow, counters don't update and just show zero for that round.
            time.sleep(1)
            # Print immediately after sleep, shows latest results
            print_status(start, counters, old_counters)
            old_counters = copy.deepcopy(counters)

            # Stop if number of threads drop (meaning one crashed)
            if threading.active_count() < 4:
                print('Error: thread died')
                control['run'] = False

        # Wait for all threads to complete
        # @TODO: Not really necessary for when Ctrl+C is the exit method
        for i in range(0, len(threads)):
            threads[i].join()

        # This will not print on Ctrl+C but it will print if threads died and thus stop
        print('Aborting...')

    except KeyboardInterrupt:
        control['run'] = False
        print('Aborting on CTRL+C...')

    finally:
        # Always print summary, no matter the cause of stopping
        print_summary(config, start, counters, old_counters)

    # Free resources
    conn.close()


if __name__=='__main__':
    main()
