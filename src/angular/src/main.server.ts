import { bootstrapApplication, provideClientHydration } from '@angular/platform-browser';
import { provideServerRendering } from '@angular/platform-server';
import { AppComponent } from './app/app.component';

const bootstrap = () => bootstrapApplication(AppComponent, {
    providers: [
        provideClientHydration(),
        provideServerRendering(),
    ]
});

export default bootstrap;
