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

FROM_EMAIL = 'nyczoningnotifications@gmail.com'
DATETIME_FORMAT = '%A, %B %-d at %-I:%M %p'

def notify_meetings() -> None:
    logging.info('Looking up un-notified meetings')
    with sqlite3.connect(os.environ['ZONING_DB_PATH']) as conn:
        meetings = conn.execute('''
            SELECT
                m.id,
                m.datetime,
                m.pdf_url,
                json_group_array(
                    json_object('description', p.description, 'location', p.location)
                ) AS projects
            FROM meetings m
            JOIN projects p on p.meeting_id = m.id
            WHERE m.notified = false
            GROUP BY 1, 2
        ''').fetchall()

    with open('recipients.txt') as f:
        recipients = f.read().split()
        logging.info(f'recipients: {recipients}')

    logging.info(f'Found {len(meetings)} un-notified meeting(s)')
    email_client = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
    successes = []
    failures = []

    for meeting_id, when, pdf_url, projects in meetings:
        try:
            when = dt.datetime.fromisoformat(when)
            mail = Mail(from_email=FROM_EMAIL,
                        to_emails=FROM_EMAIL,
                        subject='NYC zoning meeting on {}'.format(when.strftime(DATETIME_FORMAT)),
                        html_content=to_html(when, pdf_url, json.loads(projects)))
            mail.bcc = recipients
            response = email_client.send(mail)
            logging.info(f'Sent email for meeting_id {meeting_id}: {response.status_code}')
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

    logging.info('Sending admin email')
    response = email_client.send(
        Mail(from_email=FROM_EMAIL,
             to_emails='dccohe@gmail.com',
             subject='nyczoning report',
             html_content=f'Successful meeting_ids: {successes}\nFailed meeting_ids: {failures}'))
    logging.info(f'Sent admin email: {response.status_code}')


def to_html(when: dt.datetime, pdf_url: str, projects: Iterable[Dict[str, str]]) -> str:
    table_style = style({
        'border-collapse': 'collapse',
        'border': '1px solid black',
        'table-layout': 'fixed'})
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
                line('td', 'The NYC planning commission will have a public meeting on {}.'.format(when.strftime(DATETIME_FORMAT)))
            with tag('tr'):
                line('td', f'The full agenda can be found here: {pdf_url}')

        with tag('table', table_style):
            with tag('tr'):
                for header in ('Project name and description', 'Location', 'Councilmember'):
                    line('th', header, header_style)
            for project in projects:
                parsed = Project(project['description'], project['location'])
                with tag('tr'):
                    line('td', parsed.description, cell_style(50))
                    line('td', parsed.location_str, cell_style(25))
                    line('td', parsed.council_str, cell_style(25))

    return doc.getvalue()


def style(styles: Dict[str, str]) -> Tuple[str, str]:
    return ('style', ' '.join(f'{key}: {val};' for key, val in styles.items()))


class Project:
    boroughs = '|'.join(['Brooklyn', 'Manhattan', 'Queens', 'Staten Island', 'The Bronx'])
    pattern = re.compile(
        rf'Community District (\d+) (.*[^,]),? ({boroughs}) Councilmember (.+[^,]),? District (\d+)',
        flags=re.IGNORECASE)

    def __init__(self, description: str, raw_location: str):
        self.description = description
        parsed_location = re.fullmatch(Project.pattern, ' '.join(raw_location.split()))

        if parsed_location is not None:
            cd, nhood, borough, cm, district = parsed_location.groups()
            self.location_str = f'{borough} - {nhood} (Community District {cd})'
            self.council_str = f'{cm} (District {district})'
        else:
            self.location_str = raw_location
            self.council_str = ''


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    notify_meetings()
