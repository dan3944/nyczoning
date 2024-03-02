import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { provideServerRendering } from '@angular/platform-server';
import { provideClientHydration } from '@angular/platform-browser';
import { provideHttpClient, withFetch } from '@angular/common/http';

const bootstrap = () => bootstrapApplication(AppComponent, {
    providers: [
        provideClientHydration(),
        provideServerRendering(),
        provideHttpClient(withFetch()),
    ]
});

export default bootstrap;
