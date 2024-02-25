import { HttpClient, HttpClientModule } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [HttpClientModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent implements OnInit {
  meetings: Meeting[] = [];
  selectedMeeting?: Meeting;

  constructor(private readonly http: HttpClient) {}

  ngOnInit(): void {
    this.http.get('http://127.0.0.1:5000/meetings').subscribe((json) => {
      this.meetings = (json as any[]).map(m => new Meeting(m));
      this.selectedMeeting = this.meetings[0];
    });
  }
}

const today = new Date(new Date().toDateString());

class Meeting {
  readonly id: number;
  readonly when: Date;
  readonly gcalLink: string;
  readonly pdfPath: string;
  readonly sections: Array<{name: string, projects: Project[]}>;

  constructor(json: any) {
    this.id = json['id'] as number;
    this.when = new Date(json['when']);
    this.gcalLink = json['gcal_link'];
    this.pdfPath = json['pdf_path'];

    const projects = (json['projects'] as any[]).map(p => new Project(p));
    this.sections = [
      {
        name: this.isUpcoming() ? 'Projects that will have public hearings' : 'Projects that had public hearings',
        projects: projects.filter(p => p.isPublicHearing),
      }, {
        name: this.isUpcoming() ? 'Projects that will be voted on' : 'Projects that were voted on',
        projects: projects.filter(p => !p.isPublicHearing),
      },
    ];
  }

  isUpcoming(): boolean {
    return today <= this.when;
  }

  projectCount(): number {
    return this.sections.map(section => section.projects.length).reduce((a, b) => a + b, 0);
  }
}

class Project {
  readonly councilmember: string;
  readonly description: string;
  readonly location: string;
  readonly isPublicHearing: boolean;

  constructor(json: any) {
    this.councilmember = json['councilmember'];
    this.description = json['description'];
    this.location = json['location'];
    this.isPublicHearing = json['is_public_hearing'];
  }
}
