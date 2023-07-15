import config
import download
import notify


if __name__ == '__main__':
    should_send_email = config.setup()
    download.download_pdfs()
    notify.notify_meetings(send_email=should_send_email)
