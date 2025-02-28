# Firebase Genkit Angular Streaming Sample

A real-time UI for generating RPG characters using Google's Gemini API.

## Overview

This sample application demonstrates how to implement streaming AI responses in an Angular application using Firebase Genkit and Google's Gemini API. It creates interactive RPG character profiles with dynamic content generation.

## Prerequisites

- Node.js v20+ and npm installed
- A Google Developer Gemini API key

## Setup Instructions

1. Clone the repository and install dependencies:

```bash
npm i
npm run setup
```

2. Get a Google Gemini API key:
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey) to create your API key
   - Set the environment variable:

```bash
export GOOGLE_GENAI_API_KEY=your_api_key_here
```

## Running the Application

Start the development server:

```bash
npm run genkit:dev
```

Then access the application at [http://localhost:4200/](http://localhost:4200/)

## Features

- Real-time character generation with streaming responses
- Interactive UI for customizing character attributes
- Seamless integration with Google's Gemini AI model

## Project Structure

The application is built with:
- Angular for the frontend framework
- Firebase Genkit for AI integration
- Gemini 2.0 Flash for the AI model