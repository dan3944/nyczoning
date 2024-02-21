import bs4
import datetime as dt
import fitz
import io
import logging
import os
import pandas as pd
import requests
import tabula
from urllib.parse import urlparse

import config
import db


def download_pdfs() -> None:
    url = 'https://www.nyc.gov/site/planning/about/commission-meetings.page'
    logging.info(f'Getting links from {url}')
    resp = requests.get(url)
    soup = bs4.BeautifulSoup(resp.text, features='lxml')

    with db.Connection() as conn:
        meetings_iso = {
            meeting.when.isoformat() for meeting in conn.list_meetings()
        }

    for section in soup.find_all('div', class_='section'):
        title = section.find(class_='section-title').text
        logging.info(f'Found section "{title}"')

        if 'publicmeeting' in ''.join(title.lower().split()):
            logging.info('Section is a public meeting - searching for link to PDF')

            try:
                pdf_url = next(
                    'https://nyc.gov' + link['href']
                    for link in section.find_all('a', href=True)
                    if urlparse(link['href']).path.endswith('.pdf')
                )
            except StopIteration:
                logging.info('No PDF found. Skipping this section.')
                continue

            date_text = (section.find(id='PMDATE') or section.find(id='SPMDATE')) \
                            .find(text=True, recursive=False).strip()
            when = dt.datetime.strptime(date_text, '%A, %B %d, %Y, %I:%M %p')

            if when.isoformat() in meetings_iso:
                logging.info(f'Skipping {when} because it is already in db')
            else:
                download_meeting_pdf(pdf_url, when)


def download_meeting_pdf(pdf_url: str, when: dt.datetime) -> None:
    logging.info(f'Dowloading pdf from {pdf_url}')
    pdf_bytes = requests.get(pdf_url).content
    filename = f'src/static/{when.isoformat(sep=" ")}.pdf'

    logging.info(f'Saving pdf to {filename}')
    os.makedirs('pdfs', exist_ok=True)
    with open(filename, 'wb') as f:
        f.write(pdf_bytes)

    with db.Connection() as conn:
        meeting_id = conn.insert_meeting(when, filename, pdf_url)
        df1 = read_table(pdf_bytes, 'commission votes today on:', 'public hearings today on:').assign(is_public_hearing=False)
        df2 = read_table(pdf_bytes, 'public hearings today on:').assign(is_public_hearing=True)
        all_rows = pd.concat([df1, df2]).assign(meeting_id=meeting_id)
        conn.insert_projects_df(all_rows)


def read_table(pdf_bytes, start_text=None, end_text=None):
    found_start_page = start_text is None
    columns = 'ulurp_number', 'description', 'location'
    dfs = []

    for i, page in enumerate(fitz.open('pdf', pdf_bytes)):
        if not found_start_page:
            found_start_page = bool(page.search_for(start_text))
        elif end_text is not None and page.search_for(end_text):
            break
        elif page.search_for('Meeting rules'):
            break

        if not found_start_page:
            continue

        raw_dfs = tabula.read_pdf(
            io.BytesIO(pdf_bytes),
            lattice=True,
            multiple_tables=True,
            relative_area=True,
            relative_columns=True,
            area=[0, 0, 100, 100],
            columns=[round(100 * inches / 8.5) for inches in (1.6, 3.1, 6.46)],
            pages=i + 1,
            silent=True,
            pandas_options={'header': None})

        for df in raw_dfs:
            df = df.iloc[:, 2:5]
            if not df.empty:
                dfs.append(df.set_axis(columns, axis=1))

    return pd.concat(dfs).dropna() if dfs else pd.DataFrame(columns=columns)


if __name__ == '__main__':
    config.parse_args()
    download_pdfs()
