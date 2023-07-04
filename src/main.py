import logging
import download
import notify


if __name__ == '__main__':
    # TODO: log to file
    logging.basicConfig(level=logging.INFO)
    download.download_pdfs()
    notify.notify_meetings()
