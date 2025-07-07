import { AfterViewInit, Component, ElementRef, OnInit, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';

@Component({
  selector: 'app-root',
  standalone: true,
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
  imports: [
    MatButtonModule,
    MatExpansionModule,
    MatIconModule,
    MatListModule,
    MatProgressSpinnerModule,
    MatTableModule,
  ],
})
export class AppComponent implements OnInit, AfterViewInit {
  readonly tableColumns = ['description', 'location', 'councilmember'];

  readonly meetings = signal<Meeting[]>([]);
  readonly selectedMeeting = signal<Meeting | undefined>(undefined);
  readonly errorMessage = signal<String | undefined>(undefined);
  readonly isLoading = signal(true);
  readonly isPublicHearingsExpanded = signal(false);
  readonly isVotesExpanded = signal(false);

  constructor(private elementRef: ElementRef) {}

  ngAfterViewInit(): void {
    // Create the <script> tag Mailjet uses for the email signup form.
    // Angular strips <script> tags from template files.
    const s = document.createElement('script');
    s.type = 'text/javascript';
    s.src = 'https://app.mailjet.com/pas-nc-embedded-v1.js';
    this.elementRef.nativeElement.appendChild(s);
  }

  async ngOnInit(): Promise<void> {
    try {
      const response = await fetch('meetings').then(resp => resp.json());
      this.meetings.set((response as MeetingJson[]).map(m => new Meeting(m)));
      this.selectedMeeting.set(this.meetings()[0]);
    } catch (e) {
      this.errorMessage.set(`Error: Failed to get NYC planning agendas: ${e}`)
    } finally {
      this.isLoading.set(false);
    }
  }


  selectMeeting(meeting: Meeting) {
    if (meeting == this.selectedMeeting()) return;

    this.selectedMeeting.set(meeting);
    this.isPublicHearingsExpanded.set(false);
    this.isVotesExpanded.set(false);
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
