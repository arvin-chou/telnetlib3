"""Functionally tests telnetlib3 as a server using nc(1)."""
# std imports
import subprocess
import asyncio
import locale
import codecs

# local imports
from .accessories import (
    TestTelnetServer,
    unused_tcp_port,
    event_loop,
    bind_host,
    log
)

# local
import telnetlib3

# 3rd party imports
import pytest
import pexpect


def get_netcat():
    netcat_paths=('nc',
                  'netcat',
                  '/usr/bin/nc',
                  '/usr/local/bin/nc',
                  '/bin/nc.openbsd')
    for nc_name in netcat_paths:
        prog = pexpect.which(nc_name)
        if prog is None:
            continue

        stdout, stderr = subprocess.Popen(
            [prog, '-h'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        ).communicate()

        # only openbsd netcat supports IPv6.
        # So that's the only one we'll use!
        if b'-46' in (stdout + stderr):
            return prog
    return None


@pytest.mark.skipif(get_netcat() is None,
                    reason="Requires IPv6 capable (OpenBSD-borne) nc(1)")
@pytest.mark.asyncio
def test_netcat_z(event_loop, bind_host, unused_tcp_port, log):

    waiter_closed = asyncio.Future()

    server = yield from event_loop.create_server(
        protocol_factory=lambda: TestTelnetServer(
            waiter_closed=waiter_closed,
            log=log),
        host=bind_host, port=unused_tcp_port)

    log.info('Listening on {0}'.format(server.sockets[0].getsockname()))

    netcat = yield from asyncio.create_subprocess_exec(
        get_netcat(), '-z', bind_host, '{0}'.format(unused_tcp_port),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    done, pending = yield from asyncio.wait(
        [waiter_closed, netcat.wait()],
        loop=event_loop, timeout=1)

    assert not pending, (netcat, waiter_closed)
