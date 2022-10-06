# -*- coding: utf-8 -*-
import asyncio
import hashlib
import logging
import os
import random
import string
import uuid

import jinnice.main as jinnice
import editor.main as editor
import aesthetic.main as aesthetic
import myblog.main as myblog

from volgactf.final.checker.result import Result

# region Environment variables

TEAM_IP = os.getenv('TEAM_IP', '0.0.0.0')
ROUND_DURATION = int(os.getenv('ROUND_DURATION', 30))

SKIP_JINNICE = False if os.getenv('SKIP_JINNICE') is None else True
SKIP_EDITOR = False if os.getenv('SKIP_EDITOR') is None else True
SKIP_AESTHETIC = False if os.getenv('SKIP_AESTHETIC') is None else True
SKIP_MYBLOG = False if os.getenv('SKIP_MYBLOG') is None else True

PULL_COUNT = int(os.getenv('PULL_COUNT', 5))
PRINT_STATS_EVERY_N_ROUND = int(os.getenv('PRINT_STATS_EVERY_N_ROUND', 1))
PRINT_STATS_SINGLE_COLUMN = False if os.getenv('PRINT_STATS_SINGLE_COLUMN') is None else True


# endregion Environment variables

# region Themis imitator

class Metadata(object):
    def __init__(self, round_number):
        self.round_number = round_number

    @property
    def round(self):
        return self.round_number


def add_flag_to_pool(pool_flag_labels, flag, flag_adj, pull_count=5):
    if len(pool_flag_labels) != pull_count:
        del pool_flag_labels[:]
        for _ in range(pull_count):
            pool_flag_labels.append({'flag': flag, 'label': flag_adj})
    else:
        del pool_flag_labels[0]
        pool_flag_labels.append({'flag': flag, 'label': flag_adj})


def gen_capsule():
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    # cur_flag = '{0}='.format(hashlib.md5(uuid.uuid4().bytes).hexdigest())
    return 'VolgaCTF{{{0}.{1}.{2}}}'.format(
        ''.join(random.choice(chars) for _ in range(301)),
        ''.join(random.choice(chars) for _ in range(301)),
        ''.join(random.choice(chars) for _ in range(301))
    )


def print_stats(services):
    template = '''\
  Service      **{name}**
  Latest PUSH
    status:    {push_status}
    message:   {push_message}
  Latest PULL
    status:    {pull_status}
    message:   {pull_message}

  Statistics (PUSH){padding}    Statistics (PULL)
    UP:      {push_up: <{n}}      UP:      {pull_up: <{n}}
    MUMBLE:  {push_mumble: <{n}}      MUMBLE:  {pull_mumble: <{n}}
    CORRUPT: {push_corrupt: <{n}}      CORRUPT: {pull_corrupt: <{n}}
    DOWN:    {push_down: <{n}}      DOWN:    {pull_down: <{n}}
    TOTAL:   {push_total: <{n}}      TOTAL:   {pull_total: <{n}}\
'''
    stats = []
    for service_name, _, _, _, latest, push_stats, pull_stats in services:
        n = max(6, *[len(s) for s in map(str, list(push_stats.values()) + list(pull_stats.values()))])
        m = n - 6
        s = template.format(
            name=service_name,
            push_status=latest['push']['status'],
            push_message=latest['push']['message'],
            pull_status=latest['pull']['status'],
            pull_message=latest['pull']['message'],
            push_up=push_stats[Result.UP],
            padding=' ' * m,
            push_mumble=push_stats[Result.MUMBLE],
            push_corrupt=push_stats[Result.CORRUPT],
            push_down=push_stats[Result.DOWN],
            push_total=sum(push_stats.values()),
            pull_up=pull_stats[Result.UP],
            pull_mumble=pull_stats[Result.MUMBLE],
            pull_corrupt=pull_stats[Result.CORRUPT],
            pull_down=pull_stats[Result.DOWN],
            pull_total=sum(pull_stats.values()),
            n=n,
        )
        stats.append(s)

    max_width = max([max([len(r) for r in s.split('\n')]) for s in stats])
    border = '=' * max_width
    if PRINT_STATS_SINGLE_COLUMN or len(stats) < 2:
        for s in stats:
            print('{0}\n{1}\n{0}'.format(border, s))
    else:
        for sl, sr in zip(stats[0::2], stats[1::2]):
            print('{0:<{width}}{0:<{width}}'.format(border, width=max_width + 4))
            for sll, srl in zip(sl.split('\n'), sr.split('\n')):
                print('{0:<{width}}{1:<{width}}'.format(sll, srl, width=max_width + 4))
            print('{0:<{width}}{0:<{width}}'.format(border, width=max_width + 4))
        if len(stats) & 1:
            print('{0}\n{1}\n{0}'.format(border, stats[-1]))


async def main(team_ip, timeout, debug=False):
    # 1. initialize logger
    level = logging.DEBUG if debug > 3 else logging.INFO
    logging.basicConfig(level=level,
                        format='[%(asctime)s %(name)-12s %(levelname)s]: %(message)s',
                        datefmt='%m/%d %H:%M:%S')
    logger = logging.getLogger('checker')
    logger.setLevel(level)

    # 2. initialize stats objects, skipping some services if required
    if SKIP_EDITOR and SKIP_AESTHETIC and SKIP_MYBLOG and SKIP_JINNICE:
        logger.info('All the four services are skipped - nothing to do...')
        return

    services = []
    if not SKIP_EDITOR:
        services.append(('editor', editor.push, editor.pull))
    if not SKIP_AESTHETIC:
        services.append(('aesthetic', aesthetic.push, aesthetic.pull))
    if not SKIP_MYBLOG:
        services.append(('myblog', myblog.push, myblog.pull))
    if not SKIP_JINNICE:
        services.append(('jinnice', jinnice.push, jinnice.pull))
    services = [
        (
            service_name,
            push_fn,
            pull_fn,
            [],
            {'push': {'status': '', 'message': ''}, 'pull': {'status': '', 'message': ''}},
            {r: 0 for r in Result},
            {r: 0 for r in Result},
        )
        for service_name, push_fn, pull_fn in services
    ]

    # 3. start the simulation
    round_number = 0
    while True:
        round_number += 1
        logger.info('Round %d', round_number)

        for service_name, push_fn, pull_fn, pool_flag_labels, latest, push_stats, pull_stats in services:
            logger.info('[%d]  Push-pulling service %s', round_number, service_name)

            md = Metadata(round_number)
            label = hashlib.md5(uuid.uuid4().bytes).hexdigest()[:16]
            cur_flag = gen_capsule()

            logger.info('[%d]  Pushing flag %s', round_number, cur_flag)
            cur_res, label, message = await push_fn(team_ip, cur_flag, label, md)
            logger.info('[%d]  Status=%s, message="%s"', round_number, cur_res, message)
            push_stats[cur_res] += 1
            latest['push']['status'] = cur_res.name
            latest['push']['message'] = message
            if cur_res == Result.UP:
                add_flag_to_pool(pool_flag_labels, cur_flag, label, pull_count=PULL_COUNT)

            for i in range(len(pool_flag_labels)):
                cur_flag = pool_flag_labels[i]['flag']
                label = pool_flag_labels[i]['label']
                logger.info('[%d]  Pulling flag %s', round_number, cur_flag)
                cur_res, message = await pull_fn(team_ip, cur_flag, label, md)
                logger.info('[%d]  Status=%s, message="%s"', round_number, cur_res, message)
                pull_stats[cur_res] += 1
                latest['pull']['status'] = cur_res.name
                latest['pull']['message'] = message
            logger.info('')

        if PRINT_STATS_EVERY_N_ROUND > 0 and round_number % PRINT_STATS_EVERY_N_ROUND == 0:
            print_stats(services)

        await asyncio.sleep(timeout)


# endregion Themis imitator


if __name__ == '__main__':
    # start the checker
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(TEAM_IP, ROUND_DURATION))
    loop.close()
