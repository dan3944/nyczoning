import aiohttp
import asyncio
import logging
import os
import yattag
from typing import Dict, List, Tuple

import config
import db

ADMIN = 'dccohe@gmail.com'

class Notifier:
    def __init__(self, args: config.NotifierArgs, session: aiohttp.ClientSession, dbconn: db.Connection):
        self.args = args
        self.session = session
        self.dbconn = dbconn

    async def notify_meetings(self) -> None:
        logging.info('Looking up un-notified meetings')
        meetings = await self.dbconn.list_meetings(
            id=self.args.meeting_id,
            notified=False if self.args.meeting_id is None else None
        )

        logging.info(f'Found {len(meetings)} meeting(s) matching the criteria')
        resps = await asyncio.gather(*map(self._send_meeting, meetings))

        if self.args.send != config.SendType.local:
            await self.dbconn.set_notified([m.id for m in meetings], True)
            resp = await self._mailjet_post('v3.1/send', {
                'Messages': [{
                    'From': {
                        'Email': 'nycplanning@danielthemaniel.com',
                        'Name': 'NYC Planning Notifications',
                    },
                    'To': [{'Email': ADMIN}],
                    'Subject': 'nyczoning report',
                    'TextPart': str(resps),
                }],
            })
            logging.info(f'Sent admin email: {resp}')

    async def _send_meeting(self, meeting: db.Meeting):
        subject = f'NYC zoning meeting on {meeting.when:%A, %B %-d}'
        content = to_html(meeting)

        if self.args.send == config.SendType.local:
            filename = f'{subject}.html'
            logging.info(f'Writing to {filename}')
            with open(filename, 'w') as f:
                f.write(content)
            return {'file': filename}

        draft_id = (await self._mailjet_post('v3/REST/campaigndraft', {
            'Locale': 'en_US',
            'Sender': 'NYC Planning Notifications',
            'SenderEmail': 'nycplanning@danielthemaniel.com',
            'Subject': subject,
            'ContactsListID':
                '10560187' if self.args.send == config.SendType.all_contacts
                else '10560183',
        }))['Data'][0]['ID']
        await self._mailjet_post(f'v3/REST/campaigndraft/{draft_id}/detailcontent', {'Html-part': content})
        return await self._mailjet_post(f'v3/REST/campaigndraft/{draft_id}/send', {})

    async def _mailjet_post(self, url: str, content: dict) -> dict:
        url = os.path.join('https://api.mailjet.com', url)
        async with self.session.post(url, json=content, auth=mailjet_auth()) as resp:
            resp.raise_for_status()
            return await resp.json()


def to_html(meeting: db.Meeting) -> str:
    table_style = style({
        'border-collapse': 'collapse',
        'border': '1px solid black',
        'table-layout': 'fixed',
        'margin-top': '20px'})
    header_style = style({
        'font-size': '14pt',
        'padding': '16px 8px',
        'border': '1px solid black'})
    cell_style = lambda width: style({
        'font-size': '11pt',
        'padding': '16px 8px',
        'border': '1px solid black',
        'width': f'{width}%'})

    doc, tag, text, line = yattag.Doc().ttl()
    with tag('html', style({'font-family': 'sans-serif'})):
        with tag('table'):
            with tag('tr'):
                line('td', f'The NYC planning commission will have a public meeting on {meeting.when:%A, %B %-d at %-I:%M %p}.')
            with tag('tr'):
                line('td', 'Location: 120 Broadway, New York, NY 10271')
            with tag('tr'):
                with tag('td'):
                    line('a', 'Add this meeting to your Google Calendar', ('href', meeting.gcal_link()), ('target', '_blank'))
            with tag('tr'):
                with tag('td'):
                    text('The full agenda can be found ')
                    line('a', 'here', ('href', meeting.pdf_url), ('target', '_blank'))
                    text('.')

        public_hearings = [p for p in meeting.projects if p.is_public_hearing]
        commission_votes = [p for p in meeting.projects if not p.is_public_hearing]

        for projects, title in [(public_hearings, 'Projects that will have public hearings'),
                                (commission_votes, 'Projects that will be voted on')]:
            with tag('table', table_style):
                with tag('thead'):
                    with tag('tr'):
                        line('th', title, header_style, ('colspan', '3'))
                    if projects:
                        with tag('tr'):
                            for header in ('Name and description', 'Location', 'Councilmember'):
                                line('th', header, header_style)
                if projects:
                    with tag('tbody'):
                        for project in projects:
                            with tag('tr'):
                                line('td', project.description, cell_style(50))
                                line('td', project.location, cell_style(25))
                                line('td', project.councilmember, cell_style(25))
                else:
                    with tag('tbody'):
                        with tag('tr'):
                            line('td', 'None found', cell_style(100))

        line('a', 'Click here to unsubscribe', ('href', '[[UNSUB_LINK]]'), ('target', '_blank'))


    return doc.getvalue()


def style(styles: Dict[str, str]) -> Tuple[str, str]:
    return ('style', ' '.join(f'{key}: {val};' for key, val in styles.items()))


def mailjet_auth() -> aiohttp.BasicAuth:
    return aiohttp.BasicAuth(os.environ['MAILJET_APIKEY'], os.environ['MAILJET_SECRET'])


async def main(args: config.NotifierArgs):
    async with aiohttp.ClientSession() as session, db.Connection() as conn:
        await Notifier(args, session, conn).notify_meetings()


if __name__ == '__main__':
    args = config.parse_args()
    asyncio.run(main(args))
