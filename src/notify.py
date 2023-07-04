import json
import logging
import os
# import re
import sqlite3
import yagmail
# from collections import namedtuple
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
    with sqlite3.connect(os.env['ZONING_DB_PATH']) as conn:
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
    successes = []
    failures = []

    with yagmail.SMTP('nyczoningnotifications@gmail.com', os.env['ZONING_EMAIL_PW']) as yag:
        for meeting_id, when, projects in meetings:
            try:
                # TODO: bcc saved recipients
                yag.send('dccohe@gmail.com',
                         f'Public meeting at {when}',
                         to_html(json.loads(projects)))
                logging.info(f'Sent email for meeting_id {meeting_id}')
                successes.append(meeting_id)
            except:
                logging.exception(f'Failed to send email for meeting_id {meeting_id}')
                failures.append(meeting_id)

    logging.info(f'Setting notified to true for meeting_ids {successes}')
    with sqlite3.connect(os.env['ZONING_DB_PATH']) as conn:
        conn.execute(f'''
            UPDATE meetings
            SET notified = true
            WHERE id IN ( {','.join('?' * len(successes))} )
        ''', successes)

    logging.info('Sending admin email')
    with yagmail.SMTP('nyczoningnotifications@gmail.com', 'kdxssmyrmcbpifsm') as yag:
        yag.send('dccohe@gmail.com',
                 'nyczoning report',
                 f'Successful meeting_ids: {successes}\nFailed meeting_ids: {failures}')

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
