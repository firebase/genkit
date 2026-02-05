#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""FastAPI backend for Model Performance Tool."""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from typing import Any, List, Dict
import logging
from pathlib import Path

# Import tool logic
from test_model_performance import discover_models, run_model_test, parse_config_schema

app = FastAPI(title="Model Performance Tool")

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---

class Scenario(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str
    user_prompt: str

class TestRequest(BaseModel):
    model: str
    config: Dict[str, Any]
    scenario_id: str
    user_prompt: str
    system_prompt: str

class TestResult(BaseModel):
    success: bool
    response: str | None
    error: str | None
    timing: float

# --- Scenarios ---

SCENARIOS = [
    Scenario(
        id="basic_math",
        name="Basic Logic & Math",
        description="Tests reasoning capabilities with simple math problems.",
        system_prompt="You are a helpful math assistant.",
        user_prompt="What is 15 * 7? Explain step by step."
    ),
    Scenario(
        id="creative_writing",
        name="Creative Writing",
        description="Tests creativity and tone adherence.",
        system_prompt="You are a pirate bard.",
        user_prompt="Write a short poem about the ocean."
    ),
    Scenario(
        id="code_gen",
        name="Code Generation",
        description="Tests code generation capabilities.",
        system_prompt="You are an expert Python developer.",
        user_prompt="Write a function to calculate the Fibonacci sequence."
    ),
    Scenario(
        id="image_gen",
        name="Image Generation",
        description="Tests image generation models (Vertex AI only).",
        system_prompt="",
        user_prompt="A futuristic cityscape at sunset, neon lights, cyberpunk style."
    )
]

# --- Endpoints ---

@app.get("/api/scenarios", response_model=List[Scenario])
async def get_scenarios():
    return SCENARIOS

@app.get("/api/models")
async def get_models(scenario: str | None = None):
    try:
        models = await discover_models()
        
        # Simple filtering logic based on scenario
        filtered_models = []
        for name, info in models.items():
            # For specific scenarios, we might want to filter models if possible
            # But currently we don't have enough metadata to distinguish text vs image clearly 
            # except by name convention or inspecting supported actions deeper.
            # For now, we return all models and let the user choose.
            
            # Extract config schema for UI
            config_schema = info.get('customOptions', {})
            params = parse_config_schema(config_schema)
            
            filtered_models.append({
                "name": name,
                "info": info,
                "params": params
            })
            
        return filtered_models
    except Exception as e:
        logging.error(f"Error discovering models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run", response_model=TestResult)
async def run_test(request: TestRequest):
    try:
        script_path = Path(__file__).parent / "run_single_model_test.py"
        
        # Run test in thread pool to not block async loop (subprocess call inside)
        result = await asyncio.to_thread(
            lambda: asyncio.run(run_wrapper(
                request.model,
                request.config,
                request.user_prompt,
                request.system_prompt,
                script_path
            ))
        )
        
        return TestResult(
            success=result.get("success", False),
            response=str(result.get("response")) if result.get("response") else None,
            error=result.get("error"),
            timing=result.get("timing", 0.0)
        )

    except Exception as e:
        logging.error(f"Error running test: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Wrapper to run async run_model_test inside the thread
async def run_wrapper(model, config, user_prompt, system_prompt, script_path):
    # run_model_test in test_model_performance is synchronous (uses subprocess.run)
    # We need to call it directly. Wait, run_model_test in test_model_performance IS synchronous wrapper around subprocess.
    # So we don't need asyncio.run inside the lambda unless run_model_test was async.
    # Checking test_model_performance.py... run_model_test is synchronous.
    
    return run_model_test(
        model,
        config,
        user_prompt,
        system_prompt,
        script_path
    )


# Mount static files (Frontend)
app.mount("/", StaticFiles(directory="samples/sample-test/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
