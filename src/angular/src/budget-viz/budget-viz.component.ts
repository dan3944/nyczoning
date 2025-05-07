import { Component, OnInit } from '@angular/core';
import * as d3 from 'd3';
import * as d3Sankey from 'd3-sankey';

@Component({
  selector: 'budget-viz',
  standalone: true,
  imports: [],
  templateUrl: './budget-viz.component.html',
  styleUrl: './budget-viz.component.scss'
})
export class BudgetVizComponent implements OnInit {
  ngOnInit(): void {
    const sankey = d3Sankey.sankey();
  }
}
