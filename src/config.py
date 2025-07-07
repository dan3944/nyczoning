import aiohttp
import argparse
import datetime as dt
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SendType(Enum):
    local = 'local'
    admin = 'admin'
    all_contacts = 'all_contacts'

    def __str__(self):
        return self.value


@dataclass
class NotifierArgs:
    send: SendType
    meeting_id: Optional[int]


def parse_args() -> NotifierArgs:
    parser = argparse.ArgumentParser(prog='NYC Zoning Notifier')
    parser.add_argument('-l', '--logdir', help='Directory to store log files')
    parser.add_argument('-m', '--meeting_id', type=int,
                        help='Which meeting to notify for. If unspecified, notifies all un-notified meetings.')
    parser.add_argument('--send', type=SendType, default=SendType.local, choices=list(SendType),
                        help='Who to send emails to')
    args = parser.parse_args()

    if args.logdir:
        os.makedirs(args.logdir, exist_ok=True)
        logfile = f'{args.logdir}/{dt.datetime.now().isoformat()}.log'
    else:
        logfile = None

    logging.basicConfig(level=logging.INFO, filename=logfile)
    return NotifierArgs(send=args.send, meeting_id=args.meeting_id)
