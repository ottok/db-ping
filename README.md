# db-ping

MariaDB/MySQL compatible database connection and capability checker

This tool helps to quickly identify database connectivity issues such as:
- DNS propagation delay, hostname not matching active database server
- TCP/IP routing issues, server not reachable
- TLS certificate issues
- Authentication errors
- Server load issues: too many connections, too many queries or too much load
- Server health issues: disk write operations stalled or other I/O delay

## Under development

This tool is in very early stages of development and not intended for general use yet.

The code has a lot of commented-out incomplete sections, and it hasn't been refactored to clean up boilerplate code etc. But it runs! :)
