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
 * Travel itinerary output schema.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TravelItinerary {

    @JsonProperty("tripName")
    private String tripName;

    @JsonProperty("destination")
    private String destination;

    @JsonProperty("duration")
    private Integer duration;

    @JsonProperty("dailyItinerary")
    private List<DayPlan> dailyItinerary;

    @JsonProperty("estimatedBudget")
    private Budget estimatedBudget;

    @JsonProperty("packingList")
    private List<String> packingList;

    @JsonProperty("travelTips")
    private List<String> travelTips;

    // Getters and setters
    public String getTripName() {
        return tripName;
    }

    public void setTripName(String tripName) {
        this.tripName = tripName;
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

    public List<DayPlan> getDailyItinerary() {
        return dailyItinerary;
    }

    public void setDailyItinerary(List<DayPlan> dailyItinerary) {
        this.dailyItinerary = dailyItinerary;
    }

    public Budget getEstimatedBudget() {
        return estimatedBudget;
    }

    public void setEstimatedBudget(Budget estimatedBudget) {
        this.estimatedBudget = estimatedBudget;
    }

    public List<String> getPackingList() {
        return packingList;
    }

    public void setPackingList(List<String> packingList) {
        this.packingList = packingList;
    }

    public List<String> getTravelTips() {
        return travelTips;
    }

    public void setTravelTips(List<String> travelTips) {
        this.travelTips = travelTips;
    }

    /**
     * Day plan with activities.
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class DayPlan {
        @JsonProperty("day")
        private Integer day;

        @JsonProperty("title")
        private String title;

        @JsonProperty("activities")
        private List<Activity> activities;

        public Integer getDay() {
            return day;
        }

        public void setDay(Integer day) {
            this.day = day;
        }

        public String getTitle() {
            return title;
        }

        public void setTitle(String title) {
            this.title = title;
        }

        public List<Activity> getActivities() {
            return activities;
        }

        public void setActivities(List<Activity> activities) {
            this.activities = activities;
        }
    }

    /**
     * Activity within a day.
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Activity {
        @JsonProperty("time")
        private String time;

        @JsonProperty("activity")
        private String activity;

        @JsonProperty("location")
        private String location;

        @JsonProperty("estimatedCost")
        private String estimatedCost;

        @JsonProperty("tips")
        private String tips;

        public String getTime() {
            return time;
        }

        public void setTime(String time) {
            this.time = time;
        }

        public String getActivity() {
            return activity;
        }

        public void setActivity(String activity) {
            this.activity = activity;
        }

        public String getLocation() {
            return location;
        }

        public void setLocation(String location) {
            this.location = location;
        }

        public String getEstimatedCost() {
            return estimatedCost;
        }

        public void setEstimatedCost(String estimatedCost) {
            this.estimatedCost = estimatedCost;
        }

        public String getTips() {
            return tips;
        }

        public void setTips(String tips) {
            this.tips = tips;
        }
    }

    /**
     * Budget breakdown.
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Budget {
        @JsonProperty("accommodation")
        private String accommodation;

        @JsonProperty("food")
        private String food;

        @JsonProperty("activities")
        private String activities;

        @JsonProperty("transportation")
        private String transportation;

        @JsonProperty("total")
        private String total;

        public String getAccommodation() {
            return accommodation;
        }

        public void setAccommodation(String accommodation) {
            this.accommodation = accommodation;
        }

        public String getFood() {
            return food;
        }

        public void setFood(String food) {
            this.food = food;
        }

        public String getActivities() {
            return activities;
        }

        public void setActivities(String activities) {
            this.activities = activities;
        }

        public String getTransportation() {
            return transportation;
        }

        public void setTransportation(String transportation) {
            this.transportation = transportation;
        }

        public String getTotal() {
            return total;
        }

        public void setTotal(String total) {
            this.total = total;
        }
    }
}
