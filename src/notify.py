import json
import logging
import os
# import re
import sqlite3
# from collections import namedtuple
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from typing import Dict, Iterable #, Optional


# Location = namedtuple('Location', ['cd', 'nhood', 'borough', 'cm', 'district'])
# boroughs = '|'.join(['Brooklyn', 'Manhattan', 'Queens', 'Staten Island', 'The Bronx'])
# location_pattern = re.compile(
#     rf'Community District (\d+) (.*[^,]),? ({boroughs}) Councilmember (.+[^,]),? District (\d+)',
#     flags=re.IGNORECASE)

# def parse_location(text: str) -> Optional[Location]:
#     parsed = re.fullmatch(location_pattern, text)
#     if parsed:
#         cd_num, nhood, borough, cm, district = parsed.groups()
#         return Location(int(cd_num), nhood, borough, cm, int(district))


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

    logging.info(f'Found {len(meetings)} un-notified meeting(s)')
    email_client = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
    successes = []
    failures = []

    for meeting_id, when, projects in meetings:
        try:
            # TODO: bcc saved recipients
            response = email_client.send(
                Mail(from_email='nyczoningnotifications@gmail.com',
                     to_emails='dccohe@gmail.com',
                     subject=f'Public meeting at {when}',
                     html_content=to_html(json.loads(projects))))
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


# TODO: prettify email
def to_html(projects: Iterable[Dict[str, str]]) -> str:
    def to_html_row(project):
        return '<tr><td>{description}</td><td>{location}</td></tr>'.format(**project)

    return f'''
        <table>
            <tr><th>Name and description</th><th>Location</th></tr>
            {"".join(map(to_html_row, projects))}
        </table>
    '''


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    notify_meetings()
