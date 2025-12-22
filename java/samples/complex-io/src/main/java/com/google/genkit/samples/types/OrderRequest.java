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
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Complex order input demonstrating nested types.
 */
public class OrderRequest {

  @JsonProperty("customerId")
  private String customerId;

  @JsonProperty("customer")
  private Customer customer;

  @JsonProperty("items")
  private List<OrderItem> items;

  @JsonProperty("shippingAddress")
  private Address shippingAddress;

  @JsonProperty("billingAddress")
  private Address billingAddress;

  @JsonProperty("paymentMethod")
  private PaymentMethod paymentMethod;

  @JsonProperty("orderNotes")
  private String orderNotes;

  @JsonProperty("metadata")
  private Map<String, Object> metadata;

  // Nested types
  public static class Customer {
    @JsonProperty("id")
    private String id;

    @JsonProperty("firstName")
    private String firstName;

    @JsonProperty("lastName")
    private String lastName;

    @JsonProperty("email")
    private String email;

    @JsonProperty("phone")
    private String phone;

    @JsonProperty("preferences")
    private CustomerPreferences preferences;

    // Getters and setters
    public String getId() {
      return id;
    }
    public void setId(String id) {
      this.id = id;
    }
    public String getFirstName() {
      return firstName;
    }
    public void setFirstName(String firstName) {
      this.firstName = firstName;
    }
    public String getLastName() {
      return lastName;
    }
    public void setLastName(String lastName) {
      this.lastName = lastName;
    }
    public String getEmail() {
      return email;
    }
    public void setEmail(String email) {
      this.email = email;
    }
    public String getPhone() {
      return phone;
    }
    public void setPhone(String phone) {
      this.phone = phone;
    }
    public CustomerPreferences getPreferences() {
      return preferences;
    }
    public void setPreferences(CustomerPreferences preferences) {
      this.preferences = preferences;
    }
  }

  public static class CustomerPreferences {
    @JsonProperty("communicationChannel")
    private String communicationChannel; // email, sms, phone

    @JsonProperty("marketingOptIn")
    private Boolean marketingOptIn;

    @JsonProperty("language")
    private String language;

    // Getters and setters
    public String getCommunicationChannel() {
      return communicationChannel;
    }
    public void setCommunicationChannel(String communicationChannel) {
      this.communicationChannel = communicationChannel;
    }
    public Boolean getMarketingOptIn() {
      return marketingOptIn;
    }
    public void setMarketingOptIn(Boolean marketingOptIn) {
      this.marketingOptIn = marketingOptIn;
    }
    public String getLanguage() {
      return language;
    }
    public void setLanguage(String language) {
      this.language = language;
    }
  }

  public static class OrderItem {
    @JsonProperty("productId")
    private String productId;

    @JsonProperty("name")
    private String name;

    @JsonProperty("quantity")
    private Integer quantity;

    @JsonProperty("unitPrice")
    private Double unitPrice;

    @JsonProperty("discount")
    private Discount discount;

    @JsonProperty("customizations")
    private List<Customization> customizations;

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
    public Double getUnitPrice() {
      return unitPrice;
    }
    public void setUnitPrice(Double unitPrice) {
      this.unitPrice = unitPrice;
    }
    public Discount getDiscount() {
      return discount;
    }
    public void setDiscount(Discount discount) {
      this.discount = discount;
    }
    public List<Customization> getCustomizations() {
      return customizations;
    }
    public void setCustomizations(List<Customization> customizations) {
      this.customizations = customizations;
    }
  }

  public static class Discount {
    @JsonProperty("type")
    private String type; // percentage, fixed

    @JsonProperty("value")
    private Double value;

    @JsonProperty("code")
    private String code;

    // Getters and setters
    public String getType() {
      return type;
    }
    public void setType(String type) {
      this.type = type;
    }
    public Double getValue() {
      return value;
    }
    public void setValue(Double value) {
      this.value = value;
    }
    public String getCode() {
      return code;
    }
    public void setCode(String code) {
      this.code = code;
    }
  }

  public static class Customization {
    @JsonProperty("type")
    private String type;

    @JsonProperty("value")
    private String value;

    @JsonProperty("additionalCost")
    private Double additionalCost;

    // Getters and setters
    public String getType() {
      return type;
    }
    public void setType(String type) {
      this.type = type;
    }
    public String getValue() {
      return value;
    }
    public void setValue(String value) {
      this.value = value;
    }
    public Double getAdditionalCost() {
      return additionalCost;
    }
    public void setAdditionalCost(Double additionalCost) {
      this.additionalCost = additionalCost;
    }
  }

  public static class Address {
    @JsonProperty("street1")
    private String street1;

    @JsonProperty("street2")
    private String street2;

    @JsonProperty("city")
    private String city;

    @JsonProperty("state")
    private String state;

    @JsonProperty("postalCode")
    private String postalCode;

    @JsonProperty("country")
    private String country;

    @JsonProperty("coordinates")
    private Coordinates coordinates;

    // Getters and setters
    public String getStreet1() {
      return street1;
    }
    public void setStreet1(String street1) {
      this.street1 = street1;
    }
    public String getStreet2() {
      return street2;
    }
    public void setStreet2(String street2) {
      this.street2 = street2;
    }
    public String getCity() {
      return city;
    }
    public void setCity(String city) {
      this.city = city;
    }
    public String getState() {
      return state;
    }
    public void setState(String state) {
      this.state = state;
    }
    public String getPostalCode() {
      return postalCode;
    }
    public void setPostalCode(String postalCode) {
      this.postalCode = postalCode;
    }
    public String getCountry() {
      return country;
    }
    public void setCountry(String country) {
      this.country = country;
    }
    public Coordinates getCoordinates() {
      return coordinates;
    }
    public void setCoordinates(Coordinates coordinates) {
      this.coordinates = coordinates;
    }
  }

  public static class Coordinates {
    @JsonProperty("latitude")
    private Double latitude;

    @JsonProperty("longitude")
    private Double longitude;

    // Getters and setters
    public Double getLatitude() {
      return latitude;
    }
    public void setLatitude(Double latitude) {
      this.latitude = latitude;
    }
    public Double getLongitude() {
      return longitude;
    }
    public void setLongitude(Double longitude) {
      this.longitude = longitude;
    }
  }

  public static class PaymentMethod {
    @JsonProperty("type")
    private String type; // credit_card, debit_card, paypal, bank_transfer

    @JsonProperty("details")
    private PaymentDetails details;

    // Getters and setters
    public String getType() {
      return type;
    }
    public void setType(String type) {
      this.type = type;
    }
    public PaymentDetails getDetails() {
      return details;
    }
    public void setDetails(PaymentDetails details) {
      this.details = details;
    }
  }

  public static class PaymentDetails {
    @JsonProperty("lastFourDigits")
    private String lastFourDigits;

    @JsonProperty("cardType")
    private String cardType;

    @JsonProperty("expirationMonth")
    private Integer expirationMonth;

    @JsonProperty("expirationYear")
    private Integer expirationYear;

    // Getters and setters
    public String getLastFourDigits() {
      return lastFourDigits;
    }
    public void setLastFourDigits(String lastFourDigits) {
      this.lastFourDigits = lastFourDigits;
    }
    public String getCardType() {
      return cardType;
    }
    public void setCardType(String cardType) {
      this.cardType = cardType;
    }
    public Integer getExpirationMonth() {
      return expirationMonth;
    }
    public void setExpirationMonth(Integer expirationMonth) {
      this.expirationMonth = expirationMonth;
    }
    public Integer getExpirationYear() {
      return expirationYear;
    }
    public void setExpirationYear(Integer expirationYear) {
      this.expirationYear = expirationYear;
    }
  }

  // Main class getters and setters
  public String getCustomerId() {
    return customerId;
  }
  public void setCustomerId(String customerId) {
    this.customerId = customerId;
  }
  public Customer getCustomer() {
    return customer;
  }
  public void setCustomer(Customer customer) {
    this.customer = customer;
  }
  public List<OrderItem> getItems() {
    return items;
  }
  public void setItems(List<OrderItem> items) {
    this.items = items;
  }
  public Address getShippingAddress() {
    return shippingAddress;
  }
  public void setShippingAddress(Address shippingAddress) {
    this.shippingAddress = shippingAddress;
  }
  public Address getBillingAddress() {
    return billingAddress;
  }
  public void setBillingAddress(Address billingAddress) {
    this.billingAddress = billingAddress;
  }
  public PaymentMethod getPaymentMethod() {
    return paymentMethod;
  }
  public void setPaymentMethod(PaymentMethod paymentMethod) {
    this.paymentMethod = paymentMethod;
  }
  public String getOrderNotes() {
    return orderNotes;
  }
  public void setOrderNotes(String orderNotes) {
    this.orderNotes = orderNotes;
  }
  public Map<String, Object> getMetadata() {
    return metadata;
  }
  public void setMetadata(Map<String, Object> metadata) {
    this.metadata = metadata;
  }
}
