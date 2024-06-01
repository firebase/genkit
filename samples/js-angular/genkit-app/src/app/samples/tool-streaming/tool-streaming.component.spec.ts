import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ToolStreamingComponent } from './tool-streaming.component';

describe('ToolStreamingComponent', () => {
  let component: ToolStreamingComponent;
  let fixture: ComponentFixture<ToolStreamingComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ToolStreamingComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(ToolStreamingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
