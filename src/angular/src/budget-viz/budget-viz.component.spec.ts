import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BudgetVizComponent } from './budget-viz.component';

describe('BudgetVizComponentComponent', () => {
  let component: BudgetVizComponent;
  let fixture: ComponentFixture<BudgetVizComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BudgetVizComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BudgetVizComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
