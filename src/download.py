import aiohttp
import asyncio
import datetime as dt
import fitz
import io
import logging
import os
import pandas as pd
import tabula

import config
import db


class Downloader:
    def __init__(self, session: aiohttp.ClientSession, dbconn: db.Connection):
        self.session = session
        self.dbconn = dbconn

    async def download_pdfs(self) -> None:
        url = 'https://www.nyc.gov/assets/planning/json/content/calendar/calendar.json'
        logging.info(f'Getting links from {url}')

        async with self.session.get(url) as resp:
            resp_json = await resp.json()

        meetings = await self.dbconn.list_meetings()
        meetings_iso = { meeting.when.isoformat() for meeting in meetings }
        pdf_downloads = []

        for event in resp_json:
            title = event.get('title', '')

            if 'publicmeeting' not in ''.join(title.lower().split()):
                logging.info(f'Skipping "{title}" because it is not a public meeting.')
                continue

            if not event.get('agendaLink'):
                logging.info(f'Skipping "{title}" because it does not have an agenda yet.')
                continue

            # e.g. "April 7, 2025 1:00 PM"
            date_text = '{date} {startTime}'.format(**event)
            when = dt.datetime.strptime(date_text, '%B %d, %Y %I:%M %p')
            if when.isoformat() in meetings_iso:
                logging.info(f'Skipping "{title}" because it is already in db.')
                continue

            pdf_downloads.append(self.download_meeting_pdf(event['agendaLink'], when))

        await asyncio.gather(*pdf_downloads)

    async def download_meeting_pdf(self, pdf_url: str, when: dt.datetime) -> None:
        logging.info(f'Dowloading pdf from {pdf_url}')
        async with self.session.get(pdf_url) as resp:
            pdf_bytes = await resp.read()
        filename = f'src/static/{when.isoformat(sep=" ")}.pdf'

        logging.info(f'Saving pdf to {filename}')
        os.makedirs('pdfs', exist_ok=True)
        with open(filename, 'wb') as f:
            f.write(pdf_bytes)

        meeting_id = await self.dbconn.insert_meeting(when, filename, pdf_url)
        df1 = read_table(pdf_bytes, 'commission votes today on:', 'public hearings today on:').assign(is_public_hearing=False)
        df2 = read_table(pdf_bytes, 'public hearings today on:').assign(is_public_hearing=True)
        all_rows = pd.concat([df1, df2]).assign(meeting_id=meeting_id)
        await self.dbconn.insert_projects_df(all_rows)


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


async def main():
    async with aiohttp.ClientSession() as session, db.Connection() as conn:
        await Downloader(session, conn).download_pdfs()


if __name__ == '__main__':
    config.parse_args()
    asyncio.run(main())
