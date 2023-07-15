import argparse
import datetime as dt
import logging
import os

def setup():
    parser = argparse.ArgumentParser(prog='NYC Zoning Notifier')
    parser.add_argument('-l', '--logdir', help='Directory to store log files')
    parser.add_argument('--email', action='store_true', help='Whether to send emails')
    args = parser.parse_args()

    if args.logdir:
        os.makedirs(args.logdir, exist_ok=True)
        logfile = f'{args.logdir}/{dt.datetime.now().isoformat()}.log'
    else:
        logfile = None

    logging.basicConfig(level=logging.INFO, filename=logfile)
    return args.email
