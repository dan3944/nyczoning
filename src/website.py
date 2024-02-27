import dataclasses
import flask

import db


app = flask.Flask(__name__)


@app.route('/')
def home() -> str:
    return flask.render_template('index.html')


@app.route('/nycplanning')
def angular() -> flask.Response:
    return flask.send_from_directory('static/dist/browser', 'index.html')


@app.route('/<path:path>')
def static_proxy(path) -> flask.Response:
    return flask.send_from_directory('static/dist/browser', path)


@app.route('/meetings')
def meetings() -> flask.Response:
    with db.Connection() as conn:
        meetings = conn.list_meetings()
    meetings.sort(key=lambda meeting: meeting.when, reverse=True)
    return flask.jsonify(list(map(_to_dict, meetings)))


def _to_dict(meeting: db.Meeting) -> dict:
    d = dataclasses.asdict(meeting)
    d['pdf_path'] = f'/static/{meeting.when.isoformat(sep=" ")}.pdf'
    d['gcal_link'] = meeting.gcal_link()
    for project in d['projects']:
        project['description'] = project['description'].replace('\r', ' ')
    return d
