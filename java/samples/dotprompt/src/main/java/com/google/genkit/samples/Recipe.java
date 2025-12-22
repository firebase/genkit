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

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.JsonDeserializer;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * Recipe output schema for dotprompt.
 * Uses aliases and custom deserializers to handle various formats LLMs might return.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class Recipe {

    @JsonProperty("title")
    @JsonAlias({"name", "recipeName", "recipe_name"})
    private String title;

    @JsonProperty("ingredients")
    private List<Ingredient> ingredients;

    @JsonProperty("steps")
    @JsonAlias({"instructions", "directions", "procedure"})
    @JsonDeserialize(using = StepsDeserializer.class)
    private List<String> steps;

    @JsonProperty("prepTime")
    private String prepTime;

    @JsonProperty("cookTime")
    private String cookTime;

    @JsonProperty("servings")
    private Integer servings;

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public List<Ingredient> getIngredients() {
        return ingredients;
    }

    public void setIngredients(List<Ingredient> ingredients) {
        this.ingredients = ingredients;
    }

    public List<String> getSteps() {
        return steps;
    }

    public void setSteps(List<String> steps) {
        this.steps = steps;
    }

    public String getPrepTime() {
        return prepTime;
    }

    public void setPrepTime(String prepTime) {
        this.prepTime = prepTime;
    }

    public String getCookTime() {
        return cookTime;
    }

    public void setCookTime(String cookTime) {
        this.cookTime = cookTime;
    }

    public Integer getServings() {
        return servings;
    }

    public void setServings(Integer servings) {
        this.servings = servings;
    }

    @Override
    public String toString() {
        return "Recipe{" +
                "title='" + title + '\'' +
                ", ingredients=" + ingredients +
                ", steps=" + steps +
                ", prepTime='" + prepTime + '\'' +
                ", cookTime='" + cookTime + '\'' +
                ", servings=" + servings +
                '}';
    }

    /**
     * Ingredient with name and quantity.
     * Handles various field names and types LLMs might return.
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Ingredient {
        @JsonProperty("name")
        @JsonAlias({"ingredient", "item"})
        private String name;

        @JsonProperty("quantity")
        @JsonDeserialize(using = QuantityDeserializer.class)
        private String quantity;

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }

        public String getQuantity() {
            return quantity;
        }

        public void setQuantity(String quantity) {
            this.quantity = quantity;
        }

        @Override
        public String toString() {
            return "Ingredient{name='" + name + "', quantity='" + quantity + "'}";
        }
    }

    /**
     * Custom deserializer for steps/instructions that can be either:
     * - Array of strings: ["step1", "step2"]
     * - Array of objects: [{"step": 1, "title": "...", "details": "..."}]
     */
    public static class StepsDeserializer extends JsonDeserializer<List<String>> {
        @Override
        public List<String> deserialize(JsonParser p, DeserializationContext ctxt) throws IOException {
            List<String> steps = new ArrayList<>();
            JsonNode node = p.getCodec().readTree(p);
            
            if (node.isArray()) {
                for (JsonNode item : node) {
                    if (item.isTextual()) {
                        steps.add(item.asText());
                    } else if (item.isObject()) {
                        // Handle object format: {step, title, details}
                        StringBuilder sb = new StringBuilder();
                        if (item.has("title")) {
                            sb.append(item.get("title").asText());
                        }
                        if (item.has("details")) {
                            if (sb.length() > 0) sb.append(": ");
                            sb.append(item.get("details").asText());
                        }
                        if (sb.length() == 0 && item.has("description")) {
                            sb.append(item.get("description").asText());
                        }
                        if (sb.length() == 0 && item.has("instruction")) {
                            sb.append(item.get("instruction").asText());
                        }
                        steps.add(sb.length() > 0 ? sb.toString() : item.toString());
                    }
                }
            }
            return steps;
        }
    }

    /**
     * Custom deserializer for quantity that handles various formats:
     * - String: "2 cups"
     * - Number: 2.5
     * - Object with amount/unit: {"amount": 2, "unit": "cups"}
     */
    public static class QuantityDeserializer extends JsonDeserializer<String> {
        @Override
        public String deserialize(JsonParser p, DeserializationContext ctxt) throws IOException {
            JsonNode node = p.getCodec().readTree(p);
            
            if (node.isTextual()) {
                return node.asText();
            } else if (node.isNumber()) {
                return node.asText();
            } else if (node.isObject()) {
                StringBuilder sb = new StringBuilder();
                if (node.has("amount")) {
                    sb.append(node.get("amount").asText());
                }
                if (node.has("unit")) {
                    if (sb.length() > 0) sb.append(" ");
                    sb.append(node.get("unit").asText());
                }
                return sb.toString();
            }
            return node.toString();
        }
    }
}
