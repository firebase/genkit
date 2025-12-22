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

package com.google.genkit.samples.types;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Complex order response demonstrating deeply nested output types.
 */
public class OrderResponse {

  @JsonProperty("orderId")
  private String orderId;

  @JsonProperty("status")
  private String status;

  @JsonProperty("customer")
  private CustomerSummary customer;

  @JsonProperty("orderSummary")
  private OrderSummary orderSummary;

  @JsonProperty("shipping")
  private ShippingInfo shipping;

  @JsonProperty("payment")
  private PaymentInfo payment;

  @JsonProperty("timeline")
  private List<TimelineEvent> timeline;

  @JsonProperty("recommendations")
  private List<Recommendation> recommendations;

  @JsonProperty("analytics")
  private OrderAnalytics analytics;

  // Nested types
  public static class CustomerSummary {
    @JsonProperty("id")
    private String id;

    @JsonProperty("fullName")
    private String fullName;

    @JsonProperty("email")
    private String email;

    @JsonProperty("loyaltyTier")
    private String loyaltyTier;

    @JsonProperty("totalOrders")
    private Integer totalOrders;

    // Getters and setters
    public String getId() {
      return id;
    }
    public void setId(String id) {
      this.id = id;
    }
    public String getFullName() {
      return fullName;
    }
    public void setFullName(String fullName) {
      this.fullName = fullName;
    }
    public String getEmail() {
      return email;
    }
    public void setEmail(String email) {
      this.email = email;
    }
    public String getLoyaltyTier() {
      return loyaltyTier;
    }
    public void setLoyaltyTier(String loyaltyTier) {
      this.loyaltyTier = loyaltyTier;
    }
    public Integer getTotalOrders() {
      return totalOrders;
    }
    public void setTotalOrders(Integer totalOrders) {
      this.totalOrders = totalOrders;
    }
  }

  public static class OrderSummary {
    @JsonProperty("itemCount")
    private Integer itemCount;

    @JsonProperty("items")
    private List<ProcessedItem> items;

    @JsonProperty("subtotal")
    private MoneyAmount subtotal;

    @JsonProperty("discounts")
    private List<AppliedDiscount> discounts;

    @JsonProperty("tax")
    private TaxInfo tax;

    @JsonProperty("shipping")
    private MoneyAmount shipping;

    @JsonProperty("total")
    private MoneyAmount total;

    // Getters and setters
    public Integer getItemCount() {
      return itemCount;
    }
    public void setItemCount(Integer itemCount) {
      this.itemCount = itemCount;
    }
    public List<ProcessedItem> getItems() {
      return items;
    }
    public void setItems(List<ProcessedItem> items) {
      this.items = items;
    }
    public MoneyAmount getSubtotal() {
      return subtotal;
    }
    public void setSubtotal(MoneyAmount subtotal) {
      this.subtotal = subtotal;
    }
    public List<AppliedDiscount> getDiscounts() {
      return discounts;
    }
    public void setDiscounts(List<AppliedDiscount> discounts) {
      this.discounts = discounts;
    }
    public TaxInfo getTax() {
      return tax;
    }
    public void setTax(TaxInfo tax) {
      this.tax = tax;
    }
    public MoneyAmount getShipping() {
      return shipping;
    }
    public void setShipping(MoneyAmount shipping) {
      this.shipping = shipping;
    }
    public MoneyAmount getTotal() {
      return total;
    }
    public void setTotal(MoneyAmount total) {
      this.total = total;
    }
  }

  public static class ProcessedItem {
    @JsonProperty("productId")
    private String productId;

    @JsonProperty("name")
    private String name;

    @JsonProperty("quantity")
    private Integer quantity;

    @JsonProperty("unitPrice")
    private MoneyAmount unitPrice;

    @JsonProperty("totalPrice")
    private MoneyAmount totalPrice;

    @JsonProperty("customizations")
    private List<String> customizations;

    @JsonProperty("estimatedDelivery")
    private String estimatedDelivery;

    // Getters and setters
    public String getProductId() {
      return productId;
    }
    public void setProductId(String productId) {
      this.productId = productId;
    }
    public String getName() {
      return name;
    }
    public void setName(String name) {
      this.name = name;
    }
    public Integer getQuantity() {
      return quantity;
    }
    public void setQuantity(Integer quantity) {
      this.quantity = quantity;
    }
    public MoneyAmount getUnitPrice() {
      return unitPrice;
    }
    public void setUnitPrice(MoneyAmount unitPrice) {
      this.unitPrice = unitPrice;
    }
    public MoneyAmount getTotalPrice() {
      return totalPrice;
    }
    public void setTotalPrice(MoneyAmount totalPrice) {
      this.totalPrice = totalPrice;
    }
    public List<String> getCustomizations() {
      return customizations;
    }
    public void setCustomizations(List<String> customizations) {
      this.customizations = customizations;
    }
    public String getEstimatedDelivery() {
      return estimatedDelivery;
    }
    public void setEstimatedDelivery(String estimatedDelivery) {
      this.estimatedDelivery = estimatedDelivery;
    }
  }

  public static class MoneyAmount {
    @JsonProperty("amount")
    private Double amount;

    @JsonProperty("currency")
    private String currency;

    @JsonProperty("formatted")
    private String formatted;

    // Getters and setters
    public Double getAmount() {
      return amount;
    }
    public void setAmount(Double amount) {
      this.amount = amount;
    }
    public String getCurrency() {
      return currency;
    }
    public void setCurrency(String currency) {
      this.currency = currency;
    }
    public String getFormatted() {
      return formatted;
    }
    public void setFormatted(String formatted) {
      this.formatted = formatted;
    }
  }

  public static class AppliedDiscount {
    @JsonProperty("code")
    private String code;

    @JsonProperty("description")
    private String description;

    @JsonProperty("savedAmount")
    private MoneyAmount savedAmount;

    // Getters and setters
    public String getCode() {
      return code;
    }
    public void setCode(String code) {
      this.code = code;
    }
    public String getDescription() {
      return description;
    }
    public void setDescription(String description) {
      this.description = description;
    }
    public MoneyAmount getSavedAmount() {
      return savedAmount;
    }
    public void setSavedAmount(MoneyAmount savedAmount) {
      this.savedAmount = savedAmount;
    }
  }

  public static class TaxInfo {
    @JsonProperty("rate")
    private Double rate;

    @JsonProperty("amount")
    private MoneyAmount amount;

    @JsonProperty("breakdown")
    private List<TaxBreakdown> breakdown;

    // Getters and setters
    public Double getRate() {
      return rate;
    }
    public void setRate(Double rate) {
      this.rate = rate;
    }
    public MoneyAmount getAmount() {
      return amount;
    }
    public void setAmount(MoneyAmount amount) {
      this.amount = amount;
    }
    public List<TaxBreakdown> getBreakdown() {
      return breakdown;
    }
    public void setBreakdown(List<TaxBreakdown> breakdown) {
      this.breakdown = breakdown;
    }
  }

  public static class TaxBreakdown {
    @JsonProperty("type")
    private String type;

    @JsonProperty("rate")
    private Double rate;

    @JsonProperty("amount")
    private MoneyAmount amount;

    // Getters and setters
    public String getType() {
      return type;
    }
    public void setType(String type) {
      this.type = type;
    }
    public Double getRate() {
      return rate;
    }
    public void setRate(Double rate) {
      this.rate = rate;
    }
    public MoneyAmount getAmount() {
      return amount;
    }
    public void setAmount(MoneyAmount amount) {
      this.amount = amount;
    }
  }

  public static class ShippingInfo {
    @JsonProperty("method")
    private String method;

    @JsonProperty("carrier")
    private String carrier;

    @JsonProperty("trackingNumber")
    private String trackingNumber;

    @JsonProperty("estimatedDelivery")
    private DateRange estimatedDelivery;

    @JsonProperty("address")
    private FormattedAddress address;

    // Getters and setters
    public String getMethod() {
      return method;
    }
    public void setMethod(String method) {
      this.method = method;
    }
    public String getCarrier() {
      return carrier;
    }
    public void setCarrier(String carrier) {
      this.carrier = carrier;
    }
    public String getTrackingNumber() {
      return trackingNumber;
    }
    public void setTrackingNumber(String trackingNumber) {
      this.trackingNumber = trackingNumber;
    }
    public DateRange getEstimatedDelivery() {
      return estimatedDelivery;
    }
    public void setEstimatedDelivery(DateRange estimatedDelivery) {
      this.estimatedDelivery = estimatedDelivery;
    }
    public FormattedAddress getAddress() {
      return address;
    }
    public void setAddress(FormattedAddress address) {
      this.address = address;
    }
  }

  public static class DateRange {
    @JsonProperty("earliest")
    private String earliest;

    @JsonProperty("latest")
    private String latest;

    // Getters and setters
    public String getEarliest() {
      return earliest;
    }
    public void setEarliest(String earliest) {
      this.earliest = earliest;
    }
    public String getLatest() {
      return latest;
    }
    public void setLatest(String latest) {
      this.latest = latest;
    }
  }

  public static class FormattedAddress {
    @JsonProperty("lines")
    private List<String> lines;

    @JsonProperty("formatted")
    private String formatted;

    // Getters and setters
    public List<String> getLines() {
      return lines;
    }
    public void setLines(List<String> lines) {
      this.lines = lines;
    }
    public String getFormatted() {
      return formatted;
    }
    public void setFormatted(String formatted) {
      this.formatted = formatted;
    }
  }

  public static class PaymentInfo {
    @JsonProperty("status")
    private String status;

    @JsonProperty("method")
    private String method;

    @JsonProperty("transactionId")
    private String transactionId;

    @JsonProperty("billingAddress")
    private FormattedAddress billingAddress;

    // Getters and setters
    public String getStatus() {
      return status;
    }
    public void setStatus(String status) {
      this.status = status;
    }
    public String getMethod() {
      return method;
    }
    public void setMethod(String method) {
      this.method = method;
    }
    public String getTransactionId() {
      return transactionId;
    }
    public void setTransactionId(String transactionId) {
      this.transactionId = transactionId;
    }
    public FormattedAddress getBillingAddress() {
      return billingAddress;
    }
    public void setBillingAddress(FormattedAddress billingAddress) {
      this.billingAddress = billingAddress;
    }
  }

  public static class TimelineEvent {
    @JsonProperty("timestamp")
    private String timestamp;

    @JsonProperty("event")
    private String event;

    @JsonProperty("description")
    private String description;

    @JsonProperty("actor")
    private String actor;

    // Getters and setters
    public String getTimestamp() {
      return timestamp;
    }
    public void setTimestamp(String timestamp) {
      this.timestamp = timestamp;
    }
    public String getEvent() {
      return event;
    }
    public void setEvent(String event) {
      this.event = event;
    }
    public String getDescription() {
      return description;
    }
    public void setDescription(String description) {
      this.description = description;
    }
    public String getActor() {
      return actor;
    }
    public void setActor(String actor) {
      this.actor = actor;
    }
  }

  public static class Recommendation {
    @JsonProperty("productId")
    private String productId;

    @JsonProperty("name")
    private String name;

    @JsonProperty("reason")
    private String reason;

    @JsonProperty("price")
    private MoneyAmount price;

    @JsonProperty("score")
    private Double score;

    // Getters and setters
    public String getProductId() {
      return productId;
    }
    public void setProductId(String productId) {
      this.productId = productId;
    }
    public String getName() {
      return name;
    }
    public void setName(String name) {
      this.name = name;
    }
    public String getReason() {
      return reason;
    }
    public void setReason(String reason) {
      this.reason = reason;
    }
    public MoneyAmount getPrice() {
      return price;
    }
    public void setPrice(MoneyAmount price) {
      this.price = price;
    }
    public Double getScore() {
      return score;
    }
    public void setScore(Double score) {
      this.score = score;
    }
  }

  public static class OrderAnalytics {
    @JsonProperty("processingTime")
    private String processingTime;

    @JsonProperty("fraudRiskScore")
    private Double fraudRiskScore;

    @JsonProperty("customerLifetimeValue")
    private MoneyAmount customerLifetimeValue;

    @JsonProperty("tags")
    private List<String> tags;

    // Getters and setters
    public String getProcessingTime() {
      return processingTime;
    }
    public void setProcessingTime(String processingTime) {
      this.processingTime = processingTime;
    }
    public Double getFraudRiskScore() {
      return fraudRiskScore;
    }
    public void setFraudRiskScore(Double fraudRiskScore) {
      this.fraudRiskScore = fraudRiskScore;
    }
    public MoneyAmount getCustomerLifetimeValue() {
      return customerLifetimeValue;
    }
    public void setCustomerLifetimeValue(MoneyAmount customerLifetimeValue) {
      this.customerLifetimeValue = customerLifetimeValue;
    }
    public List<String> getTags() {
      return tags;
    }
    public void setTags(List<String> tags) {
      this.tags = tags;
    }
  }

  // Main class getters and setters
  public String getOrderId() {
    return orderId;
  }
  public void setOrderId(String orderId) {
    this.orderId = orderId;
  }
  public String getStatus() {
    return status;
  }
  public void setStatus(String status) {
    this.status = status;
  }
  public CustomerSummary getCustomer() {
    return customer;
  }
  public void setCustomer(CustomerSummary customer) {
    this.customer = customer;
  }
  public OrderSummary getOrderSummary() {
    return orderSummary;
  }
  public void setOrderSummary(OrderSummary orderSummary) {
    this.orderSummary = orderSummary;
  }
  public ShippingInfo getShipping() {
    return shipping;
  }
  public void setShipping(ShippingInfo shipping) {
    this.shipping = shipping;
  }
  public PaymentInfo getPayment() {
    return payment;
  }
  public void setPayment(PaymentInfo payment) {
    this.payment = payment;
  }
  public List<TimelineEvent> getTimeline() {
    return timeline;
  }
  public void setTimeline(List<TimelineEvent> timeline) {
    this.timeline = timeline;
  }
  public List<Recommendation> getRecommendations() {
    return recommendations;
  }
  public void setRecommendations(List<Recommendation> recommendations) {
    this.recommendations = recommendations;
  }
  public OrderAnalytics getAnalytics() {
    return analytics;
  }
  public void setAnalytics(OrderAnalytics analytics) {
    this.analytics = analytics;
  }
}
