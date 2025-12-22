/*
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
 *
 * SPDX-License-Identifier: Apache-2.0
 */

package com.google.genkit.samples;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * Input schema for travel planning.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TravelInput {

    @JsonProperty("destination")
    private String destination;

    @JsonProperty("duration")
    private Integer duration;

    @JsonProperty("budget")
    private String budget;

    @JsonProperty("interests")
    private List<String> interests;

    @JsonProperty("travelStyle")
    private String travelStyle;

    public TravelInput() {}

    public TravelInput(String destination, Integer duration, String budget) {
        this.destination = destination;
        this.duration = duration;
        this.budget = budget;
    }

    public String getDestination() {
        return destination;
    }

    public void setDestination(String destination) {
        this.destination = destination;
    }

    public Integer getDuration() {
        return duration;
    }

    public void setDuration(Integer duration) {
        this.duration = duration;
    }

    public String getBudget() {
        return budget;
    }

    public void setBudget(String budget) {
        this.budget = budget;
    }

    public List<String> getInterests() {
        return interests;
    }

    public void setInterests(List<String> interests) {
        this.interests = interests;
    }

    public String getTravelStyle() {
        return travelStyle;
    }

    public void setTravelStyle(String travelStyle) {
        this.travelStyle = travelStyle;
    }

    @Override
    public String toString() {
        return "TravelInput{destination='" + destination + "', duration=" + duration + 
               ", budget='" + budget + "', interests=" + interests + 
               ", travelStyle='" + travelStyle + "'}";
    }
}
