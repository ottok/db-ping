# db-ping

**MariaDB/MySQL compatible database connection and capability checker**

Is your database connection unstable? Do you want to know the SLA of your
database connection over a longer period, or just quickly measure how long of a
downtime a database restart or some other operation caused? When the database
isn't serving queries, do you want to know exacly why?

This tool helps to measure and identify database connectivity issues such as:
- Downtime duration and SLA
- DNS propagation delay, hostname not matching active database server
- TCP/IP routing issues, server not reachable
- TLS certificate issues
- Authentication errors
- Server load issues: too many connections, too many queries or too much load
- Server health issues: disk write operations stalled or other I/O delay

![Demo of db-ping](db-ping.gif)

## Under development

This tool is in very early stages of development and not intended for general
use yet, but it does run and can be tested.
