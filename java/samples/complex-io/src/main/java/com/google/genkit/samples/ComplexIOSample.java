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

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.core.Flow;
import com.google.genkit.plugins.jetty.JettyPlugin;
import com.google.genkit.plugins.jetty.JettyPluginOptions;
import com.google.genkit.plugins.openai.OpenAIPlugin;
import com.google.genkit.samples.types.*;

/**
 * Sample application demonstrating complex input/output types with Genkit
 * flows.
 * 
 * This sample shows how to: - Use deeply nested object types - Handle arrays
 * and collections - Work with optional fields - Process maps and generic types
 * - Handle complex domain objects
 */
public class ComplexIOSample {

  public static void main(String[] args) throws Exception {
    // Create the Jetty server plugin
    JettyPlugin jetty = new JettyPlugin(JettyPluginOptions.builder().port(8080).build());

    // Initialize Genkit with plugins
    Genkit genkit = Genkit.builder().options(GenkitOptions.builder().devMode(true).reflectionPort(3100).build())
        .plugin(OpenAIPlugin.create()).plugin(jetty).build();

    // Flow 1: Process complex order with nested types
    Flow<OrderRequest, OrderResponse, Void> processOrder = genkit.defineFlow("processOrder", OrderRequest.class,
        OrderResponse.class, (request) -> {
          // This flow demonstrates processing complex nested input
          // and generating a complex nested response

          // In a real implementation, you would:
          // 1. Validate the order
          // 2. Calculate pricing with discounts
          // 3. Process payment
          // 4. Generate shipping details
          // 5. Create timeline and recommendations

          OrderResponse response = new OrderResponse();
          response.setOrderId("ORD-" + System.currentTimeMillis());
          response.setStatus("CONFIRMED");

          // Set customer summary
          OrderResponse.CustomerSummary customerSummary = new OrderResponse.CustomerSummary();
          if (request.getCustomer() != null) {
            customerSummary.setId(request.getCustomer().getId());
            customerSummary.setFullName(
                request.getCustomer().getFirstName() + " " + request.getCustomer().getLastName());
            customerSummary.setEmail(request.getCustomer().getEmail());
          }
          customerSummary.setLoyaltyTier("Gold");
          customerSummary.setTotalOrders(15);
          response.setCustomer(customerSummary);

          // Set order summary with calculated values
          OrderResponse.OrderSummary orderSummary = new OrderResponse.OrderSummary();
          orderSummary.setItemCount(request.getItems() != null ? request.getItems().size() : 0);

          // Calculate totals
          double subtotal = 0.0;
          if (request.getItems() != null) {
            for (OrderRequest.OrderItem item : request.getItems()) {
              subtotal += item.getQuantity() * item.getUnitPrice();
            }
          }

          OrderResponse.MoneyAmount subtotalAmount = new OrderResponse.MoneyAmount();
          subtotalAmount.setAmount(subtotal);
          subtotalAmount.setCurrency("USD");
          subtotalAmount.setFormatted(String.format("$%.2f", subtotal));
          orderSummary.setSubtotal(subtotalAmount);

          OrderResponse.MoneyAmount totalAmount = new OrderResponse.MoneyAmount();
          double tax = subtotal * 0.08;
          double total = subtotal + tax + 9.99; // shipping
          totalAmount.setAmount(total);
          totalAmount.setCurrency("USD");
          totalAmount.setFormatted(String.format("$%.2f", total));
          orderSummary.setTotal(totalAmount);

          response.setOrderSummary(orderSummary);

          // Set shipping info
          OrderResponse.ShippingInfo shippingInfo = new OrderResponse.ShippingInfo();
          shippingInfo.setMethod("Standard");
          shippingInfo.setCarrier("USPS");
          shippingInfo.setTrackingNumber("1Z999AA10123456784");

          OrderResponse.DateRange deliveryRange = new OrderResponse.DateRange();
          deliveryRange.setEarliest("2025-02-15");
          deliveryRange.setLatest("2025-02-18");
          shippingInfo.setEstimatedDelivery(deliveryRange);

          response.setShipping(shippingInfo);

          // Set timeline events
          OrderResponse.TimelineEvent event1 = new OrderResponse.TimelineEvent();
          event1.setTimestamp("2025-02-10T10:30:00Z");
          event1.setEvent("ORDER_PLACED");
          event1.setDescription("Order was placed");
          event1.setActor("customer");

          OrderResponse.TimelineEvent event2 = new OrderResponse.TimelineEvent();
          event2.setTimestamp("2025-02-10T10:30:05Z");
          event2.setEvent("PAYMENT_CONFIRMED");
          event2.setDescription("Payment was confirmed");
          event2.setActor("system");

          response.setTimeline(Arrays.asList(event1, event2));

          // Set analytics
          OrderResponse.OrderAnalytics analytics = new OrderResponse.OrderAnalytics();
          analytics.setProcessingTime("1.2s");
          analytics.setFraudRiskScore(0.05);
          analytics.setTags(Arrays.asList("new_customer", "high_value", "rush_shipping"));
          response.setAnalytics(analytics);

          return response;
        });

    // Flow 2: Generate analytics from complex request
    Flow<AnalyticsRequest, AnalyticsResponse, Void> generateAnalytics = genkit.defineFlow("generateAnalytics",
        AnalyticsRequest.class, AnalyticsResponse.class, (request) -> {
          // This flow demonstrates processing complex analytics requests
          // with filters, grouping, and metrics

          AnalyticsResponse response = new AnalyticsResponse();
          response.setRequestId("REQ-" + System.currentTimeMillis());
          response.setExecutionTime("245ms");

          // Build summary
          AnalyticsResponse.Summary summary = new AnalyticsResponse.Summary();
          summary.setTotalRecords(15234L);

          Map<String, AnalyticsResponse.MetricValue> metrics = new HashMap<>();

          AnalyticsResponse.MetricValue revenueMetric = new AnalyticsResponse.MetricValue();
          revenueMetric.setValue(1234567.89);
          revenueMetric.setFormatted("$1,234,567.89");
          AnalyticsResponse.ChangeIndicator revenueChange = new AnalyticsResponse.ChangeIndicator();
          revenueChange.setAbsolute(123456.78);
          revenueChange.setPercentage(11.1);
          revenueChange.setDirection("up");
          revenueChange.setComparisonPeriod("previous_month");
          revenueMetric.setChange(revenueChange);
          metrics.put("revenue", revenueMetric);

          AnalyticsResponse.MetricValue ordersMetric = new AnalyticsResponse.MetricValue();
          ordersMetric.setValue(5678);
          ordersMetric.setFormatted("5,678 orders");
          metrics.put("orders", ordersMetric);

          summary.setMetrics(metrics);

          // Add trend indicators
          AnalyticsResponse.TrendIndicator revenueTrend = new AnalyticsResponse.TrendIndicator();
          revenueTrend.setMetric("revenue");
          revenueTrend.setTrend("increasing");
          revenueTrend.setConfidence(0.92);

          AnalyticsResponse.ForecastPoint fp1 = new AnalyticsResponse.ForecastPoint();
          fp1.setDate("2025-03-01");
          fp1.setValue(1350000.0);
          fp1.setLower(1250000.0);
          fp1.setUpper(1450000.0);

          AnalyticsResponse.ForecastPoint fp2 = new AnalyticsResponse.ForecastPoint();
          fp2.setDate("2025-04-01");
          fp2.setValue(1450000.0);
          fp2.setLower(1300000.0);
          fp2.setUpper(1600000.0);

          revenueTrend.setForecast(Arrays.asList(fp1, fp2));
          summary.setTrends(Arrays.asList(revenueTrend));

          response.setSummary(summary);

          // Build data result
          AnalyticsResponse.DataResult dataResult = new AnalyticsResponse.DataResult();

          AnalyticsResponse.ColumnDefinition col1 = new AnalyticsResponse.ColumnDefinition();
          col1.setName("date");
          col1.setType("date");
          col1.setFormat("YYYY-MM-DD");

          AnalyticsResponse.ColumnDefinition col2 = new AnalyticsResponse.ColumnDefinition();
          col2.setName("revenue");
          col2.setType("currency");
          col2.setFormat("$#,##0.00");
          col2.setAggregation("sum");

          dataResult.setColumns(Arrays.asList(col1, col2));

          // Sample rows
          Map<String, Object> row1 = new HashMap<>();
          row1.put("date", "2025-02-01");
          row1.put("revenue", 45678.90);

          Map<String, Object> row2 = new HashMap<>();
          row2.put("date", "2025-02-02");
          row2.put("revenue", 52341.23);

          dataResult.setRows(Arrays.asList(row1, row2));
          response.setData(dataResult);

          // Build visualizations
          AnalyticsResponse.Visualization lineChart = new AnalyticsResponse.Visualization();
          lineChart.setId("viz-001");
          lineChart.setType("line");
          lineChart.setTitle("Revenue Over Time");

          AnalyticsResponse.VisualizationData vizData = new AnalyticsResponse.VisualizationData();
          vizData.setLabels(Arrays.asList("Jan", "Feb", "Mar", "Apr", "May"));

          AnalyticsResponse.Dataset dataset = new AnalyticsResponse.Dataset();
          dataset.setLabel("Revenue");
          dataset.setData(Arrays.asList(120000.0, 135000.0, 142000.0, 155000.0, 168000.0));
          dataset.setColor("#4285F4");
          vizData.setDatasets(Arrays.asList(dataset));

          lineChart.setData(vizData);

          AnalyticsResponse.VisualizationConfig vizConfig = new AnalyticsResponse.VisualizationConfig();
          AnalyticsResponse.AxisConfig xAxis = new AnalyticsResponse.AxisConfig();
          xAxis.setLabel("Month");
          xAxis.setType("category");
          vizConfig.setXAxis(xAxis);

          AnalyticsResponse.AxisConfig yAxis = new AnalyticsResponse.AxisConfig();
          yAxis.setLabel("Revenue ($)");
          yAxis.setType("linear");
          yAxis.setFormat("currency");
          vizConfig.setYAxis(yAxis);

          lineChart.setConfig(vizConfig);
          response.setVisualizations(Arrays.asList(lineChart));

          // Add insights
          AnalyticsResponse.Insight insight = new AnalyticsResponse.Insight();
          insight.setType("trend");
          insight.setSeverity("info");
          insight.setTitle("Strong Revenue Growth");
          insight.setDescription("Revenue has grown 11.1% compared to the previous month");
          insight.setMetrics(Arrays.asList("revenue", "orders"));

          AnalyticsResponse.SuggestedAction action = new AnalyticsResponse.SuggestedAction();
          action.setAction("Consider increasing marketing spend");
          action.setImpact("high");
          action.setEffort("medium");
          insight.setActions(Arrays.asList(action));

          response.setInsights(Arrays.asList(insight));

          // Set metadata
          AnalyticsResponse.ResponseMetadata metadata = new AnalyticsResponse.ResponseMetadata();
          metadata.setQueryId("QRY-" + System.currentTimeMillis());
          metadata.setCacheHit(false);
          metadata.setDataFreshness("2025-02-10T10:30:00Z");
          metadata.setWarnings(Arrays.asList());
          response.setMetadata(metadata);

          return response;
        });

    // Flow 3: Process batch of items with arrays
    Flow<List<String>, Map<String, Object>, Void> processBatch = genkit.defineFlow("processBatch",
        (Class<List<String>>) (Class<?>) List.class, (Class<Map<String, Object>>) (Class<?>) Map.class,
        (items) -> {
          Map<String, Object> result = new HashMap<>();
          result.put("processed", items.size());
          result.put("items", items);
          result.put("timestamp", System.currentTimeMillis());
          result.put("success", true);

          Map<String, Integer> counts = new HashMap<>();
          for (String item : items) {
            counts.merge(item, 1, Integer::sum);
          }
          result.put("itemCounts", counts);

          return result;
        });

    // Flow 4: Transform order to simplified format
    Flow<OrderRequest, Map<String, Object>, Void> simplifyOrder = genkit.defineFlow("simplifyOrder",
        OrderRequest.class, (Class<Map<String, Object>>) (Class<?>) Map.class, (order) -> {
          Map<String, Object> simplified = new HashMap<>();

          if (order.getCustomer() != null) {
            simplified.put("customerName",
                order.getCustomer().getFirstName() + " " + order.getCustomer().getLastName());
            simplified.put("email", order.getCustomer().getEmail());
          }

          if (order.getItems() != null) {
            simplified.put("itemCount", order.getItems().size());

            double total = 0.0;
            for (OrderRequest.OrderItem item : order.getItems()) {
              total += item.getQuantity() * item.getUnitPrice();
            }
            simplified.put("orderTotal", total);
          }

          if (order.getShippingAddress() != null) {
            simplified.put("shippingCity", order.getShippingAddress().getCity());
            simplified.put("shippingCountry", order.getShippingAddress().getCountry());
          }

          return simplified;
        });

    // Flow 5: Validate order structure
    Flow<OrderRequest, ValidationResult, Void> validateOrder = genkit.defineFlow("validateOrder",
        OrderRequest.class, ValidationResult.class, (order) -> {
          ValidationResult result = new ValidationResult();
          result.setValid(true);

          List<ValidationResult.ValidationError> errors = new java.util.ArrayList<>();
          List<ValidationResult.ValidationWarning> warnings = new java.util.ArrayList<>();

          // Validate customer
          if (order.getCustomer() == null) {
            ValidationResult.ValidationError error = new ValidationResult.ValidationError();
            error.setField("customer");
            error.setMessage("Customer information is required");
            error.setSeverity("error");
            errors.add(error);
            result.setValid(false);
          } else {
            if (order.getCustomer().getEmail() == null || order.getCustomer().getEmail().isEmpty()) {
              ValidationResult.ValidationError error = new ValidationResult.ValidationError();
              error.setField("customer.email");
              error.setMessage("Customer email is required");
              error.setSeverity("error");
              errors.add(error);
              result.setValid(false);
            }
          }

          // Validate items
          if (order.getItems() == null || order.getItems().isEmpty()) {
            ValidationResult.ValidationError error = new ValidationResult.ValidationError();
            error.setField("items");
            error.setMessage("Order must have at least one item");
            error.setSeverity("error");
            errors.add(error);
            result.setValid(false);
          } else {
            for (int i = 0; i < order.getItems().size(); i++) {
              OrderRequest.OrderItem item = order.getItems().get(i);
              if (item.getQuantity() == null || item.getQuantity() <= 0) {
                ValidationResult.ValidationError error = new ValidationResult.ValidationError();
                error.setField("items[" + i + "].quantity");
                error.setMessage("Item quantity must be greater than 0");
                error.setSeverity("error");
                errors.add(error);
                result.setValid(false);
              }
              if (item.getQuantity() != null && item.getQuantity() > 100) {
                ValidationResult.ValidationWarning warning = new ValidationResult.ValidationWarning();
                warning.setField("items[" + i + "].quantity");
                warning.setMessage("Large quantity order - manual review recommended");
                warnings.add(warning);
              }
            }
          }

          // Validate shipping address
          if (order.getShippingAddress() == null) {
            ValidationResult.ValidationError error = new ValidationResult.ValidationError();
            error.setField("shippingAddress");
            error.setMessage("Shipping address is required");
            error.setSeverity("error");
            errors.add(error);
            result.setValid(false);
          }

          result.setErrors(errors);
          result.setWarnings(warnings);
          result.setErrorCount(errors.size());
          result.setWarningCount(warnings.size());

          return result;
        });

    System.out.println("Complex I/O Sample started!");
    System.out.println("Available flows:");
    System.out.println("  - processOrder: Process complex nested order request");
    System.out.println("  - generateAnalytics: Generate analytics from complex request");
    System.out.println("  - processBatch: Process batch of items");
    System.out.println("  - simplifyOrder: Transform order to simplified format");
    System.out.println("  - validateOrder: Validate order structure");

    // Start the server to expose the flows
    jetty.start();
  }
}
