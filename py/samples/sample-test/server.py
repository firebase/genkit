#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""FastAPI backend for Model Performance Tool."""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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

# --- Scenarios Discovery ---

async def discover_scenarios() -> List[Scenario]:
    samples_dir = Path(__file__).parent.parent
    scenarios = []
    
    if not samples_dir.exists():
        return scenarios

    # Iterate through sample directories
    for item in sorted(samples_dir.iterdir()):
        if item.is_dir() and not item.name.startswith(('.', '_')):
            # Try to read metadata from pyproject.toml
            pyproject_path = item / "pyproject.toml"
            name = item.name
            description = "Genkit sample project"
            
            if pyproject_path.exists():
                try:
                    import tomllib # type: ignore
                    with open(pyproject_path, "rb") as f:
                        data = tomllib.load(f)
                        project = data.get("project", {})
                        name = project.get("name", name)
                        description = project.get("description", description)
                except Exception:
                    pass
            
            scenarios.append(Scenario(
                id=item.name,
                name=name,
                description=description,
                system_prompt="You are a pirate.",
                user_prompt="what is 5 + 3?"
            ))
            
    return scenarios

# We'll fetch SCENARIOS dynamically in the endpoint

# --- Endpoints ---

from fastapi.responses import HTMLResponse, JSONResponse

@app.get("/", response_class=HTMLResponse)
async def root():
    logging.info("Root path accessed")
    static_dir = Path(__file__).parent / "static"
    index_path = static_dir / "index.html"
    if not index_path.exists():
        logging.error(f"index.html not found at {index_path}")
        return HTMLResponse(content="index.html not found", status_code=404)
    return HTMLResponse(content=index_path.read_text())

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Server is running"}

@app.get("/api/scenarios", response_model=List[Scenario])
async def get_scenarios():
    return await discover_scenarios()

@app.get("/api/models")
async def get_models(sample: str | None = None):
    """Get models available for a specific sample.
    
    Args:
        sample: Sample name to discover models for (e.g., 'google-genai-hello')
        
    Returns:
        List of models with numbering, info, and parsed parameters
    """
    try:
        # Import the discovery function
        from test_model_performance import discover_models_for_sample, parse_config_schema
        
        if sample:
            logging.info(f"Discovering models for sample: {sample}")
            models = await discover_models_for_sample(sample)
        else:
            logging.info("Discovering all models")
            from test_model_performance import discover_models
            models = await discover_models()
        
        logging.info(f"Found {len(models)} models: {list(models.keys())}")
        
        # Build numbered model list
        filtered_models = []
        for idx, (name, info) in enumerate(models.items(), start=1):
            # Validate model name
            if not name or not isinstance(name, str):
                logging.warning(f"Invalid model name at index {idx}: {name}")
                continue
                
            # Extract config schema for UI
            config_schema = info.get('customOptions', {}) if isinstance(info, dict) else {}
            params = parse_config_schema(config_schema)
            
            model_entry = {
                "number": idx,
                "name": name,
                "display_name": f"{idx}. {name}",
                "info": info if isinstance(info, dict) else {},
                "params": params
            }
            
            logging.debug(f"Model entry: {model_entry['display_name']}")
            filtered_models.append(model_entry)
        
        logging.info(f"Returning {len(filtered_models)} filtered models")
        return filtered_models
    except Exception as e:
        logging.error(f"Error discovering models: {e}", exc_info=True)
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


class ComprehensiveTestRequest(BaseModel):
    sample: str
    model: str
    user_prompt: str
    system_prompt: str


class ComprehensiveTestResult(BaseModel):
    total_tests: int
    passed: int
    failed: int
    results: List[Dict[str, Any]]


@app.post("/api/run-comprehensive", response_model=ComprehensiveTestResult)
async def run_comprehensive_test(request: ComprehensiveTestRequest):
    """Run comprehensive test with all parameter variations.
    
    Tests all config parameter variations:
    1. First test with all defaults ({})
    2. Then vary one parameter at a time
    """
    try:
        from test_model_performance import (
            discover_models_for_sample,
            parse_config_schema,
            generate_config_variations,
            run_model_test
        )
        
        # Get model info
        models = await discover_models_for_sample(request.sample)
        if request.model not in models:
            raise HTTPException(status_code=404, detail=f"Model {request.model} not found in sample {request.sample}")
        
        model_info = models[request.model]
        config_schema = model_info.get('customOptions', {})
        params = parse_config_schema(config_schema)
        
        # Generate variations
        variations = generate_config_variations(params)
        
        # Run all tests
        script_path = Path(__file__).parent / "run_single_model_test.py"
        all_results = []
        
        for config in variations:
            result = await asyncio.to_thread(
                run_model_test,
                request.model,
                config,
                request.user_prompt,
                request.system_prompt,
                script_path
            )
            
            all_results.append({
                "config": config,
                "success": result.get("success", False),
                "response": result.get("response"),
                "error": result.get("error"),
                "timing": result.get("timing", 0.0)
            })
        
        # Calculate stats
        passed = sum(1 for r in all_results if r["success"])
        failed = len(all_results) - passed
        
        return ComprehensiveTestResult(
            total_tests=len(all_results),
            passed=passed,
            failed=failed,
            results=all_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error running comprehensive test: {e}")
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

# Mount static files (CSS, JS, etc.) under /static/
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
