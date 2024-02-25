from dataclasses import asdict
from flask import Flask, render_template, send_from_directory
from typing import List

import db


app = Flask(__name__)


@app.route('/')
def home() -> None:
    return render_template('index.html')


@app.route('/nycplanning')
def angular():
    return send_from_directory('static/dist/nycplanning/browser', 'index.html')


@app.route('/<path:path>')
def static_proxy(path):
  return send_from_directory('static/dist/nycplanning/browser', path)


@app.route('/meetings')
def meetings() -> List[dict]:
    with db.Connection() as conn:
        meetings = conn.list_meetings()
    meetings.sort(key=lambda meeting: meeting.when, reverse=True)
    return list(map(_to_dict, meetings))


def _to_dict(meeting: db.Meeting) -> dict:
    d = asdict(meeting)
    d['pdf_path'] = f'/static/{meeting.when.isoformat(sep=" ")}.pdf'
    d['gcal_link'] = meeting.gcal_link()
    for project in d['projects']:
        project['description'] = project['description'].replace('\r', ' ')
    return d
