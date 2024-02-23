import datetime as dt
from dataclasses import asdict
from flask import Flask, render_template

import db


app = Flask(__name__)


@app.route('/')
def home() -> None:
    return render_template('index.html')


@app.route('/nycplanning')
def nycplanning() -> None:
    with db.Connection() as conn:
        meetings = conn.list_meetings()

    meetings.sort(key=lambda meeting: meeting.when, reverse=True)
    return render_template('meetings.html', meetings=meetings)


def _is_upcoming(meeting: db.Meeting) -> bool:
    return meeting.when.date() >= dt.date.today()


def _to_dict(meeting: db.Meeting) -> str:
    d = asdict(meeting)
    d['when'] = d['when'].strftime('%A, %B %-d, %Y at %-I:%M %p')
    d['pdf_path'] = f'/static/{meeting.when.isoformat(sep=" ")}.pdf'
    d['gcal_link'] = meeting.gcal_link()
    for project in d['projects']:
        project['description'] = project['description'].replace('\r', ' ')
    return d


app.jinja_env.filters['is_upcoming'] = _is_upcoming
app.jinja_env.filters['to_dict'] = _to_dict
