import bs4
import datetime as dt
import io
import logging
import os
import pypdf
import requests
import sqlite3
import tabula
from urllib.parse import urlparse


def download_pdfs() -> None:
    url = 'https://www.nyc.gov/site/planning/about/commission-meetings.page'
    logging.info(f'Getting links from {url}')
    resp = requests.get(url)
    logging.info('Parsing HTML')
    soup = bs4.BeautifulSoup(resp.text, features='lxml')

    with sqlite3.connect(os.environ['ZONING_DB_PATH']) as conn:
        meetings_iso = {
            when for when, in conn.execute('SELECT datetime FROM meetings').fetchall()
        }

    for section in soup.find_all('div', class_='section'):
        title = section.find(class_='section-title').text
        logging.info(f'Found section "{title}"')

        if title.lower().split() == ['public', 'meeting']:
            logging.info('Section is a public meeting - searching for link to PDF')
            pdf_url = next(
                'https://nyc.gov' + link['href']
                for link in section.find_all('a', href=True)
                if urlparse(link['href']).path.endswith('.pdf')
            )
            date_text = section.find(id='PMDATE').find(text=True, recursive=False).strip()
            when = dt.datetime.strptime(date_text, '%A, %B %d, %Y, %I:%M %p')

            if when.isoformat(sep=' ') in meetings_iso:
                logging.info(f'Skipping {when} because it is already in db')
            else:
                download_meeting_pdf(pdf_url, when)


def download_meeting_pdf(pdf_url: str, when: dt.datetime) -> None:
    logging.info(f'Dowloading pdf from {pdf_url}')
    pdf_bytes = requests.get(pdf_url).content
    when_iso = when.isoformat(sep=' ')
    filename = f'pdfs/{when_iso}.pdf'
    n_pages = len(pypdf.PdfReader(io.BytesIO(pdf_bytes)).pages)

    logging.info(f'Saving pdf to {filename}')
    os.makedirs('pdfs', exist_ok=True)
    with open(filename, 'wb') as f:
        f.write(pdf_bytes)

    with sqlite3.connect(os.environ['ZONING_DB_PATH']) as conn:
        db_row = when_iso, filename, pdf_url
        logging.info(f'Inserting into database: {db_row}')
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO meetings (datetime, pdf_filename, pdf_url, notified) VALUES (?, ?, ?, False)',
            db_row)

        logging.info('Reading pdf table into dataframe')
        df = tabula.read_pdf(
            io.BytesIO(pdf_bytes),
            lattice=True,
            multiple_tables=False,
            relative_columns=[inches / 8.5 for inches in (0.56, 1.6, 3.1, 6.46, 8.15)],
            pages=list(range(3, n_pages + 1)),
        )[0] \
            .iloc[:, 1:4] \
            .dropna() \
            .set_axis(['ulurp_number', 'description', 'location'], axis=1) \
            .assign(meeting_id=cur.lastrowid)
            # .applymap(lambda text: '\n'.join(text.splitlines())) \
            # .applymap(lambda text: ' '.join(text.split())) \
    
        logging.info(f'Inserting into database:\n{df}')
        df.to_sql('projects', conn, index=False, if_exists='append')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    download_pdfs()
