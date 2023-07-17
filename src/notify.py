import datetime as dt
import json
import logging
import os
import re
import sqlite3
import yattag
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from typing import Dict, Iterable, Tuple
from urllib.parse import urlencode

import config

sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))

def notify_meetings(args: config.NotifierArgs) -> None:
    logging.info('Looking up un-notified meetings')
    with sqlite3.connect(os.environ['ZONING_DB_PATH']) as conn:
        where_clause = 'm.notified = false' if args.meeting_id is None else 'm.id = ?'
        params = () if args.meeting_id is None else (args.meeting_id,)
        meetings = conn.execute(f'''
            SELECT
                m.id,
                m.datetime,
                m.pdf_url,
                json_group_array(
                    json_object(
                        'description', p.description,
                        'location', p.location,
                        'is_public_hearing', p.is_public_hearing
                    )
                ) AS projects
            FROM meetings m
            JOIN projects p on p.meeting_id = m.id
            WHERE {where_clause}
            GROUP BY 1, 2, 3
        ''', params).fetchall()

    logging.info(f'Found {len(meetings)} meeting(s) matching the criteria')
    successes = []
    failures = []

    for meeting_id, when, pdf_url, projects in meetings:
        try:
            when = dt.datetime.fromisoformat(when)
            logging.info(f'Meeting ID: {meeting_id}')
            subject = f'NYC zoning meeting on {when:%A, %B %-d}'
            content = to_html(when, pdf_url, json.loads(projects))
            send_email(args.send, subject, content)
            successes.append(meeting_id)
        except:
            logging.exception(f'Failed to send email for meeting_id {meeting_id}')
            failures.append(meeting_id)

    logging.info(f'Setting notified to true for meeting_ids {successes}')
    with sqlite3.connect(os.environ['ZONING_DB_PATH']) as conn:
        conn.execute(f'''
            UPDATE meetings
            SET notified = true
            WHERE id IN ( {','.join('?' * len(successes))} )
        ''', successes)

    admin_content = f'Successful meeting_ids: {successes}\nFailed meeting_ids: {failures}'
    if args.send == config.SendType.local:
        logging.info(f'Admin info:\n{admin_content}')
    else:
        response = sg.send(Mail(
            from_email='nyczoningnotifications@gmail.com',
            to_emails='dccohe@gmail.com',
            subject='nyczoning report',
            plain_text_content=admin_content,
        ))
        logging.info(f'Sent admin email: {response.status_code}')


def send_email(send_type: config.SendType, subject: str, content: str) -> None:
    if send_type == config.SendType.local:
        filename = f'{subject}.html'
        logging.info(f'Writing to {filename}')
        with open(filename, 'w') as f:
            f.write(content)
        return

    resp = sg.client.marketing.singlesends.post(request_body={
        'name': f'NYC zoning notification: {dt.datetime.utcnow().isoformat()}',
        'send_to': {'all': True}
                   if send_type == config.SendType.all_contacts
                   else {'list_ids': ['2f5f6a2e-9a29-4129-aae5-235074f8ab4a']},
        'email_config': {
            'subject': subject,
            'html_content': content,
            'suppression_group_id': 23496,
            'sender_id': 5135856,
        },
    })
    ssid = json.loads(resp.body)['id']
    logging.info(f'Single Send ID: {ssid} (status code: {resp.status_code})')
    resp = sg.client.marketing.singlesends._(ssid).schedule.put(request_body={'send_at': 'now'})
    logging.info(f'Scheduled single send (status code: {resp.status_code})')


def to_html(when: dt.datetime, pdf_url: str, projects: Iterable[Dict[str, any]]) -> str:
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

    gcal_link = 'https://www.google.com/calendar/render?' + urlencode({
        'action': 'TEMPLATE',
        'text': 'NYC Planning Commission Public Meeting',
        'dates': f'{when:%Y%m%dT%H%M%S}/{when + dt.timedelta(hours=1):%Y%m%dT%H%M%S}',
        'ctz': 'America/New_York',
        'details': f'Agenda: {pdf_url}',
        'location': 'City Planning Commission Hearing Room, Lower Concourse - 120 Broadway, New York, NY 10271',
    })

    doc, tag, text, line = yattag.Doc().ttl()
    with tag('html', style({'font-family': 'sans-serif'})):
        with tag('table'):
            with tag('tr'):
                line('td', f'The NYC planning commission will have a public meeting on {when:%A, %B %-d at %-I:%M %p}.')
            with tag('tr'):
                line('td', 'Location: 120 Broadway, New York, NY 10271')
            with tag('tr'):
                with tag('td'):
                    line('a', 'Add this meeting to your Google Calendar', ('href', gcal_link), ('target', '_blank'))
            with tag('tr'):
                with tag('td'):
                    text('The full agenda can be found ')
                    line('a', 'here', ('href', pdf_url), ('target', '_blank'))
                    text('.')

        projects = list(map(Project, projects))
        public_hearings = [p for p in projects if p.is_public_hearing]
        commission_votes = [p for p in projects if not p.is_public_hearing]

        for projects, title in [(public_hearings, 'Projects that will have public hearings'),
                                (commission_votes, 'Projects that will be voted on')]:
            with tag('table', table_style):
                with tag('tr'):
                    line('th', title, header_style, ('colspan', '3'))
                with tag('tr'):
                    for header in ('Name and description', 'Location', 'Councilmember'):
                        line('th', header, header_style)
                for project in projects:
                    with tag('tr'):
                        line('td', project.description, cell_style(50))
                        line('td', project.location_str, cell_style(25))
                        line('td', project.council_str, cell_style(25))

    return doc.getvalue()


def style(styles: Dict[str, str]) -> Tuple[str, str]:
    return ('style', ' '.join(f'{key}: {val};' for key, val in styles.items()))


class Project:
    boroughs = '|'.join(['Brooklyn', 'Manhattan', 'Queens', 'Staten Island', 'The Bronx'])
    pattern = re.compile(
        rf'Community District (\d+) (.*[^,]),? ({boroughs}) Councilmember (.+[^,]),? District (\d+)',
        flags=re.IGNORECASE)

    def __init__(self, unparsed: Dict[str, any]):
        self.description = unparsed['description']
        self.is_public_hearing = bool(unparsed['is_public_hearing'])
        parsed_location = re.fullmatch(Project.pattern, ' '.join(unparsed['location'].split()))

        if parsed_location is not None:
            cd, nhood, borough, cm, district = parsed_location.groups()
            self.location_str = f'{borough} - {nhood} (Community District {cd})'
            self.council_str = f'{cm} (District {district})'
        else:
            self.location_str = unparsed['location']
            self.council_str = 'None found'


if __name__ == '__main__':
    args = config.parse_args()
    notify_meetings(args)
