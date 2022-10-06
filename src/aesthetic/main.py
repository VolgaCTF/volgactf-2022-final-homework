#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import hashlib
import logging
import os
import socket

import jwt
from volgactf.final.checker.result import Result

from .utils import read_message, send_message

logger = logging.getLogger(__name__)
SERVICE_PORT = int(os.getenv('AESTHETIC_PORT', 8777))
SESSION_TOTAL_TIMEOUT = int(os.getenv('AESTHETIC_TIMEOUT', 15))


async def push(endpoint, capsule: str, label, metadata):
    try:
        logger.debug('[%s on PUSH]: connecting', endpoint)
        fd = socket.create_connection((endpoint, SERVICE_PORT), timeout=SESSION_TOTAL_TIMEOUT)
        logger.debug('[%s on PUSH]: connected to service', endpoint)
    except Exception as ex:
        logger.error('[%s on PUSH]: failed to connect, reason: %s', endpoint, str(ex))
        return Result.DOWN, '', 'Failed to connect'

    try:
        send_message(fd, b'PUSH')

        iv = b'\x70\x67\x4a\xd5\xaf\x53\x92\xf9\xb2\x94\xde\x78' + os.urandom(4)

        send_message(fd, capsule.encode('utf-8'))
        send_message(fd, metadata.round.to_bytes(4, 'big'))
        send_message(fd, iv)

        encrypted_capsule = read_message(fd)
        ec_hash = hashlib.sha256(encrypted_capsule).digest()
        auth_tag = read_message(fd)

        with open('ec_private.pem', 'rb') as jwtkey:
            key = jwtkey.read()
        signature = jwt.encode(
            {'message': 'It\'s me, Mario!'},
            key=key,
            algorithm='ES256'
        )

        send_message(fd, signature.encode('utf-8'))

        if read_message(fd) != b"+":
            send_message(fd, b'EXIT')
            read_message(fd)
            return Result.MUMBLE, '', ''

        send_message(fd, b'EXIT')
        read_message(fd)

        return Result.UP, \
               (base64.b64encode(iv) + b'::' +
                base64.b64encode(auth_tag) + b'::' +
                base64.b64encode(ec_hash)).decode(), \
               'UP'

    except Exception as ex:
        logger.error('[%s on PUSH]: failed on PUSH, reason: %s', endpoint, str(ex))
        return Result.MUMBLE, '', ''


async def pull(endpoint, capsule: bytes, label: str, metadata):
    try:
        logger.debug('[%s on PULL]: connecting', endpoint)
        fd = socket.create_connection((endpoint, SERVICE_PORT), timeout=SESSION_TOTAL_TIMEOUT)
        logger.debug('[%s on PULL]: connected to service', endpoint)
    except Exception as ex:
        logger.error('[%s on PULL]: failed to connect, reason: %s', endpoint, str(ex))
        return Result.DOWN, ''

    try:
        b64_iv, b64_auth_tag, b64_ec_hash = label.encode().split(b'::')
        iv = base64.b64decode(b64_iv)
        auth_tag = base64.b64decode(b64_auth_tag)
        ec_hash = base64.b64decode(b64_ec_hash)

        send_message(fd, b'PULL')
        send_message(fd, metadata.round.to_bytes(4, 'big'))

        received_enc_capsule = read_message(fd)
        rec_hash = hashlib.sha256(received_enc_capsule).digest()

        if rec_hash != ec_hash:
            print(rec_hash, ec_hash)
            send_message(fd, b'-')
            send_message(fd, b'EXIT')
            read_message(fd)
            return Result.DOWN, 'Wrong hash'
        else:
            send_message(fd, b'+')

        send_message(fd, iv)
        send_message(fd, auth_tag)

        recv_capsule = read_message(fd)

        if recv_capsule.decode('utf-8') != capsule:
            send_message(fd, b'EXIT')
            read_message(fd)
            return Result.DOWN, 'Corrupted flag'

        send_message(fd, b'EXIT')
        read_message(fd)

        return Result.UP, 'UP'

    except Exception as ex:
        logger.error('[%s on PULL]: failed on PULL, reason: %s', endpoint, str(ex))
        return Result.MUMBLE, ''
