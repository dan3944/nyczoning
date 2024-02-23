import datetime as dt
from dataclasses import asdict
from flask import Flask, render_template

import db

# TODO: '%-I:%M %p' for time

app = Flask(__name__)


@app.route('/meetings')
def meetings() -> None:
    with db.Connection() as conn:
        meetings = conn.list_meetings()

    meetings.sort(key=lambda meeting: meeting.when, reverse=True)
    return render_template('meetings.html', meetings=meetings)


def _is_upcoming(meeting: db.Meeting) -> bool:
    return meeting.when.date() >= dt.date.today() - dt.timedelta(days=1) # remove


def _to_dict(meeting: db.Meeting) -> str:
    d = asdict(meeting)
    d['when'] = d['when'].strftime('%A, %B %-d %Y')
    d['pdf_path'] = f'/static/{meeting.when.isoformat(sep=" ")}.pdf'
    for project in d['projects']:
        project['description'] = project['description'].replace('\r', ' ')
    return d


app.jinja_env.filters['is_upcoming'] = _is_upcoming
app.jinja_env.filters['to_dict'] = _to_dict
