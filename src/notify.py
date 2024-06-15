import datetime as dt
import json
import logging
import os
import yattag
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from typing import Dict, Tuple

import config
import db

sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))

def notify_meetings(args: config.NotifierArgs) -> None:
    logging.info('Looking up un-notified meetings')
    with db.Connection() as conn:
        meetings = conn.list_meetings(
            id=args.meeting_id,
            notified=False if args.meeting_id is None else None)

    logging.info(f'Found {len(meetings)} meeting(s) matching the criteria')
    successes = []
    failures = {}

    for meeting in meetings:
        try:
            logging.info(f'Meeting ID: {meeting.id}')
            subject = f'NYC zoning meeting on {meeting.when:%A, %B %-d}'
            content = to_html(meeting)
            send_email(args.send, subject, content)
            successes.append(meeting.id)
        except Exception as e:
            logging.exception(f'Failed to send email for meeting_id {meeting.id}')
            failures[meeting.id] = str(e)

    with db.Connection() as conn:
        conn.set_notified(successes, True)

    admin_content = f'Successful meeting_ids: {successes}\nFailed meeting_ids: {failures}'
    if args.send == config.SendType.local:
        logging.info(f'Admin info:\n{admin_content}')
    else:
        response = sg.send(Mail(
            from_email='nycplanning@danielthemaniel.com',
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
            'sender_id': 5664084,
        },
    })
    ssid = json.loads(resp.body)['id']
    logging.info(f'Single Send ID: {ssid} (status code: {resp.status_code})')
    resp = sg.client.marketing.singlesends._(ssid).schedule.put(request_body={'send_at': 'now'})
    logging.info(f'Scheduled single send (status code: {resp.status_code})')


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
                line('td', '{{#if first_name}}Hi {{first_name}},{{/if}}')
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
                with tag('tr'):
                    line('th', title, header_style, ('colspan', '3'))
                if projects:
                    with tag('tr'):
                        for header in ('Name and description', 'Location', 'Councilmember'):
                            line('th', header, header_style)
                    for project in projects:
                        with tag('tr'):
                            line('td', project.description, cell_style(50))
                            line('td', project.location, cell_style(25))
                            line('td', project.councilmember, cell_style(25))
                else:
                    with tag('tr'):
                        line('td', 'None found', cell_style(100))

    return doc.getvalue()


def style(styles: Dict[str, str]) -> Tuple[str, str]:
    return ('style', ' '.join(f'{key}: {val};' for key, val in styles.items()))


if __name__ == '__main__':
    args = config.parse_args()
    notify_meetings(args)
