/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { TestBed, type ComponentFixture } from '@angular/core/testing';

import { StreamingJSONComponent } from './streaming-json.component';

describe('StreamingJSONComponent', () => {
  let component: StreamingJSONComponent;
  let fixture: ComponentFixture<StreamingJSONComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StreamingJSONComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(StreamingJSONComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
