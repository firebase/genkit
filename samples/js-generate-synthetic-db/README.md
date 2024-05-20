# Synthetic Dog Food Sales Database Generator (Bone Appetit)

This project leverages Genkit AI's structured output alongside the `Gemini 1.5 Pro model`, to generate synthetic sales data for a fictional dog food company called `Bone Appetit`. The generated data is then stored in a Firestore database, row by row, for further analysis or use in applications.

## Cloud Functions Version

### Prerequisites
#### Vertex AI for LLM
#### Cloud Functions for deployment
#### Firestore for database storage
#### Firebase for application

### Overview

1. Setup:

#### Import necessary libraries for AI (Genkit), Firebase, and data handling.
#### Configure Genkit to use Google's Vertex AI and set logging preferences.

2. Data Structures:

#### `Order class`: Defines the structure of each sales record (order ID, customer info, product, etc.).
#### `menuItems`: A list of dog food products and their prices.
#### `BoneAppetitSalesDatabaseSchema`: A strict schema (using Zod) to ensure generated data matches the expected format.

3. Data Generation:

#### `createBoneAppetitSalesRowSchema`: This is a Genkit flow. It takes a product as input, prompts the Gemini 1.5 Pro model, and gets back structured JSON representing one sales record.
##### The prompt instructs the AI to create realistic data, including reviews that align with customer ratings.
#### `rateLimitedRunFlowGenerator`: This is a special function to control the pace of data generation. We don't want to overwhelm the AI or hit API limits. It yields Promises that resolve to new sales data, but with pauses if needed.

4. Firestore Storage:
#### Batch write synthetic sales data to Firestore. 

#### How to deploy to Cloud Functions:
```bash
firebase deploy
``` 

## Local Version

### Prerequisites
#### Vertex AI for LLM

### Overview
This project leverages Genkit AI's structured output alongside the `Gemini 1.5 Pro model`, to generate synthetic sales data for a fictional dog food company called `Bone Appetit`. The generated data is in the form of an array of `Order objects`, each containing detailed information about a customer's purchase, including item, quantity, total sales, order status, timestamps, customer demographics, customer ratings and reviews.

#### How to run locally:
```bash
Genkit start
``` 
