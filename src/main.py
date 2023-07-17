import config
import download
import notify


if __name__ == '__main__':
    args = config.parse_args()
    download.download_pdfs()
    notify.notify_meetings(args)
