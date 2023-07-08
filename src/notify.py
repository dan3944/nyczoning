import json
import logging
import os
import re
import sqlite3
import yattag
from collections import namedtuple
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from typing import Dict, Iterable, Optional


def notify_meetings() -> None:
    logging.info('Looking up un-notified meetings')
    with sqlite3.connect(os.environ['ZONING_DB_PATH']) as conn:
        meetings = conn.execute('''
            SELECT
                m.id,
                m.datetime,
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

    for meeting_id, when, projects in meetings:
        try:
            mail = Mail(from_email='nyczoningnotifications@gmail.com',
                        to_emails='nyczoningnotifications@gmail.com',
                        subject=f'NYC zoning meeting happening on {when}',
                        html_content=to_html(json.loads(projects)))
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
        Mail(from_email='nyczoningnotifications@gmail.com',
             to_emails='dccohe@gmail.com',
             subject='nyczoning report',
             html_content=f'Successful meeting_ids: {successes}\nFailed meeting_ids: {failures}'))
    logging.info(f'Sent admin email: {response.status_code}')


def to_html(projects: Iterable[Dict[str, str]]) -> str:
    table_style = css({'border-collapse': 'collapse',
                       'border': '1px solid black',
                       'table-layout': 'fixed',
                       'font-family': 'sans-serif'})
    header_style = css({'padding': '16px 8px',
                       'font-size': '14pt',
                       'border': '1px solid black'})
    cell_style = lambda width: css({
        'padding': '16px 8px',
        'font-size': '11pt',
        'width': f'{width}%',
        'border': '1px solid black'})
    doc, tag, text = yattag.Doc().tagtext()

    with tag('table', table_style):
        with tag('tr'):
            for header in ('Name and description', 'Location', 'Councilmember'):
                with tag('th', header_style):
                    text(header)

        for project in projects:
            location = parse_location(project['location'])
            with tag('tr'):
                with tag('td', cell_style(50)):
                    text(project['description'])
                with tag('td', cell_style(25)):
                    text(f'{location.borough} - {location.nhood} (Community District {location.cd})'
                         if location else project['location'])
                with tag('td', cell_style(25)):
                    text(f'{location.cm} (District {location.district})'
                         if location else '')

    return doc.getvalue()


def css(styles):
    return ('style',
            ' '.join(f'{key}: {val};' for key, val in styles.items()))


Location = namedtuple('Location', ['cd', 'nhood', 'borough', 'cm', 'district'])
boroughs = '|'.join(['Brooklyn', 'Manhattan', 'Queens', 'Staten Island', 'The Bronx'])
location_pattern = re.compile(
    rf'Community District (\d+) (.*[^,]),? ({boroughs}) Councilmember (.+[^,]),? District (\d+)',
    flags=re.IGNORECASE)


def parse_location(text: str) -> Optional[Location]:
    parsed = re.fullmatch(location_pattern, ' '.join(text.split()))
    if parsed:
        cd_num, nhood, borough, cm, district = parsed.groups()
        return Location(int(cd_num), nhood, borough, cm, int(district))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    notify_meetings()
