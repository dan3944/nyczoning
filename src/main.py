import argparse
import datetime as dt
import logging
import os

import download
import notify


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='NYC Zoning Notifier')
    parser.add_argument('-l', '--logdir', help='Directory to store log files')
    args = parser.parse_args()

    if args.logdir:
        os.makedirs(args.logdir, exist_ok=True)
        logfile = f'{args.logdir}/{dt.datetime.now().isoformat()}.log'
    else:
        logfile = None

    logging.basicConfig(level=logging.INFO, filename=logfile)
    download.download_pdfs()
    notify.notify_meetings()
