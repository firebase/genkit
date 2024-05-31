import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StreamingJSONComponent } from './streaming-json.component';

describe('StreamingJSONComponent', () => {
  let component: StreamingJSONComponent;
  let fixture: ComponentFixture<StreamingJSONComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StreamingJSONComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(StreamingJSONComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
