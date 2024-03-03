import { Component, OnInit } from '@angular/core';

@Component({
  selector: 'app-root',
  standalone: true,
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent implements OnInit {
  meetings: Meeting[] = [];
  selectedMeeting?: Meeting;
  isLoading: boolean = true;
  errorMessage?: string

  async ngOnInit(): Promise<void> {
    try {
      const response = await fetch('meetings').then(resp => resp.json());
      this.meetings = (response as MeetingJson[]).map(m => new Meeting(m));
      this.selectedMeeting = this.meetings[0];
    } catch (e) {
      this.errorMessage = `Error: Failed to get NYC planning agendas: ${e}`;
    } finally {
      this.isLoading = false;
    }
  }
}

type ProjectJson = {
  readonly councilmember: string;
  readonly description: string;
  readonly location: string;
  readonly is_public_hearing: boolean;
};

type MeetingJson = {
  id: number,
  when: string,
  gcal_link: string,
  pdf_path: string,
  projects: ProjectJson[],
};

class Meeting {
  static readonly today = new Date(new Date().toDateString());

  readonly id: number;
  readonly when: Date;
  readonly gcalLink: string;
  readonly pdfPath: string;
  readonly sections: Array<{name: string, projects: ProjectJson[]}>;

  constructor(json: MeetingJson) {
    this.id = json.id;
    this.when = new Date(json.when);
    this.gcalLink = json.gcal_link;
    this.pdfPath = json.pdf_path;
    this.sections = [
      {
        name: this.isUpcoming() ? 'Projects that will have public hearings' : 'Projects that had public hearings',
        projects: json.projects.filter(p => p.is_public_hearing),
      }, {
        name: this.isUpcoming() ? 'Projects that will be voted on' : 'Projects that were voted on',
        projects: json.projects.filter(p => !p.is_public_hearing),
      },
    ];
  }

  isUpcoming(): boolean {
    return Meeting.today <= this.when;
  }

  projectCount(): number {
    return this.sections.reduce((count, section) => count + section.projects.length, 0);
  }
}
