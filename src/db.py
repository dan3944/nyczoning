from __future__ import annotations
import aiosqlite
import asyncio
import datetime as dt
import json
import logging
import os
import pandas as pd
import re
from dataclasses import dataclass
from urllib.parse import urlencode
from typing import ClassVar, Dict, List, Optional


@dataclass
class Project:
    description: str
    is_public_hearing: bool
    location: str
    councilmember: str

    _boroughs: ClassVar[str] = '|'.join(['Brooklyn', 'Manhattan', 'Queens', 'Staten Island', 'The Bronx'])
    _pattern: ClassVar[re.Pattern] = re.compile(
        rf'Community District (\d+) (.*[^,]),? ({_boroughs}) Councilmember (.+[^,]),? District (\d+)',
        flags=re.IGNORECASE)

    @staticmethod
    def create(unparsed: Dict[str, any]) -> Project:
        parsed_location = re.fullmatch(Project._pattern, ' '.join(unparsed['location'].split()))

        if parsed_location is not None:
            cd, nhood, borough, cm, district = parsed_location.groups()
            location_str = f'{borough} - {nhood} (Community District {cd})'
            council_str = f'{cm} (District {district})'
        else:
            location_str = unparsed['location']
            council_str = 'None found'

        return Project(
            description=unparsed['description'],
            is_public_hearing=bool(unparsed['is_public_hearing']),
            location=location_str,
            councilmember=council_str)


@dataclass
class Meeting:
    id: int
    when: dt.datetime
    pdf_url: str
    projects: List[Project]

    def gcal_link(self) -> str:
        return 'https://www.google.com/calendar/render?' + urlencode({
            'action': 'TEMPLATE',
            'text': 'NYC Planning Commission Public Meeting',
            'dates': f'{self.when:%Y%m%dT%H%M%S}/{self.when + dt.timedelta(hours=1):%Y%m%dT%H%M%S}',
            'ctz': 'America/New_York',
            'details': f'Agenda: {self.pdf_url}',
            'location': 'City Planning Commission Hearing Room, Lower Concourse - 120 Broadway, New York, NY 10271',
        })

    @staticmethod
    def create(unparsed: Dict[str, any]) -> Meeting:
        return Meeting(
            id=unparsed['id'],
            when=dt.datetime.fromisoformat(unparsed['datetime']),
            pdf_url=unparsed['pdf_url'],
            projects=[Project.create(p) for p in json.loads(unparsed['projects'])])


class Connection:
    async def __aenter__(self):
        self._conn = await aiosqlite.connect(os.environ['ZONING_DB_PATH'])
        self._conn.row_factory = aiosqlite.Row
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val is None:
            await self._conn.commit()
        await self._conn.close()

    async def insert_meeting(self, when: dt.datetime, filename: str, pdf_url: str) -> int:
        '''Returns the ID of the created meeting.'''
        db_row = when.isoformat(sep=' '), filename, pdf_url
        logging.info(f'Inserting into meetings table: {db_row}')
        result = await self._conn.execute_insert(
            'INSERT INTO meetings (datetime, pdf_filename, pdf_url, notified) VALUES (?, ?, ?, False)',
            db_row)
        return result['last_insert_rowid()']

    async def insert_projects_df(self, df: pd.DataFrame) -> None:
        logging.info(f'Inserting into projects table:\n{df}')
        await self._conn.executemany('''
            INSERT INTO projects
            ( meeting_id,  is_public_hearing,  ulurp_number,  description,  location) VALUES
            (:meeting_id, :is_public_hearing, :ulurp_number, :description, :location);
        ''', df.to_dict(orient='records'))

    async def list_meetings(self, id: Optional[int] = None, notified: Optional[bool] = None) -> List[Meeting]:
        where_clause = 'true'
        params = []
        if id is not None:
            where_clause += ' and m.id = ?'
            params.append(id)
        if notified is not None:
            where_clause += ' and m.notified = ?'
            params.append(notified)

        logging.info(f'Listing meetings: "{where_clause}", {params}')
        cur = await self._conn.execute(f'''
            SELECT
                m.id,
                m.datetime,
                m.pdf_url,
                json_group_array(
                    json_object(
                        'description', p.description,
                        'location', p.location,
                        'is_public_hearing', p.is_public_hearing
                    )
                ) AS projects
            FROM meetings m
            LEFT JOIN projects p on p.meeting_id = m.id
            WHERE {where_clause}
            GROUP BY 1, 2, 3
        ''', params)
        rows = await cur.fetchall()
        return list(map(Meeting.create, rows))

    async def set_notified(self, meeting_ids: List[int], notified: bool) -> None:
        logging.info(f'Setting notified to {notified} for meeting_ids {meeting_ids}')
        await self._conn.execute(f'''
            UPDATE meetings
            SET notified = ?
            WHERE id IN ( {','.join('?' * len(meeting_ids))} )
        ''', [notified] + meeting_ids)

    async def clear_db(self) -> None:
        await self._conn.execute('DELETE FROM meetings;')
        await self._conn.execute('DELETE FROM projects;')
