import datetime as dt
from flask import Flask, render_template

import db

# '%-I:%M %p' for time

app = Flask(__name__,
            static_url_path='',
            static_folder='static')


@app.route('/meetings')
def meetings() -> None:
    with db.Connection() as conn:
        meetings = conn.list_meetings()

    meetings.sort(key=lambda meeting: meeting.when, reverse=True)
    return render_template('meetings.html', meetings=meetings)
