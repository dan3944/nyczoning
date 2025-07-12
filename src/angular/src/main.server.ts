import { bootstrapApplication } from '@angular/platform-browser';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { AppComponent } from './app/app.component';


const bootstrap = () => bootstrapApplication(AppComponent, {
    providers: [
        provideAnimationsAsync(),
    ]
});

export default bootstrap;
