"""Setup API routes for managing initial configuration."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path
import os
import re
import subprocess
import asyncio
import shutil

router = APIRouter(prefix="/api/setup", tags=["setup"])

# Path to the .env file
ENV_FILE_PATH = Path(__file__).parent.parent.parent.parent / ".env"
SETUP_FLAG_FILE = Path(__file__).parent.parent.parent.parent / ".setup_complete"
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
LLAMA_CPP_DIR = PROJECT_ROOT / "llama.cpp"


class APIKeysRequest(BaseModel):
    """Request model for saving API keys."""
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None


class SetupStatusResponse(BaseModel):
    """Response model for setup status."""
    setup_complete: bool


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status():
    """Check if initial setup has been completed."""
    setup_complete = SETUP_FLAG_FILE.exists()
    return SetupStatusResponse(setup_complete=setup_complete)


@router.post("/save-keys")
async def save_api_keys(keys: APIKeysRequest):
    """Save API keys to the .env file."""
    try:
        # Read existing .env content
        env_content = ""
        if ENV_FILE_PATH.exists():
            with open(ENV_FILE_PATH, "r") as f:
                env_content = f.read()

        # Update or add each key
        if keys.OPENAI_API_KEY:
            env_content = update_env_variable(env_content, "OPENAI_API_KEY", keys.OPENAI_API_KEY)

        if keys.GEMINI_API_KEY:
            env_content = update_env_variable(env_content, "GEMINI_API_KEY", keys.GEMINI_API_KEY)

        # Write back to .env file
        with open(ENV_FILE_PATH, "w") as f:
            f.write(env_content)

        return {"success": True, "message": "API keys saved successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save API keys: {str(e)}")


@router.post("/complete")
async def mark_setup_complete():
    """Mark the setup as complete."""
    try:
        # Create the setup complete flag file
        SETUP_FLAG_FILE.touch()
        return {"success": True, "message": "Setup marked as complete"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark setup complete: {str(e)}")


@router.post("/reset")
async def reset_setup():
    """Reset the setup status (for testing/development)."""
    try:
        if SETUP_FLAG_FILE.exists():
            SETUP_FLAG_FILE.unlink()
        return {"success": True, "message": "Setup reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset setup: {str(e)}")


def update_env_variable(content: str, key: str, value: str) -> str:
    """Update or add an environment variable in the .env content."""
    # Pattern to match the key (with optional spaces around =)
    pattern = rf'^{re.escape(key)}\s*=.*$'

    # Check if key exists
    if re.search(pattern, content, re.MULTILINE):
        # Replace existing value
        content = re.sub(pattern, f"{key}={value}", content, flags=re.MULTILINE)
    else:
        # Add new key at the end
        if content and not content.endswith('\n'):
            content += '\n'
        content += f"{key}={value}\n"

    return content


# ==================== LLAMA.CPP SETUP ENDPOINTS ====================

@router.get("/llama-status")
async def check_llama_status():
    """Check if llama.cpp is installed and ready."""
    status = {
        "installed": False,
        "cloned": False,
        "built": False,
        "server_available": False,
        "ccache_installed": False
    }

    # Check if llama.cpp directory exists
    if LLAMA_CPP_DIR.exists():
        status["cloned"] = True

        # Check if build directory exists with binaries
        build_dir = LLAMA_CPP_DIR / "build"
        if build_dir.exists():
            # Check for llama-server binary
            llama_server = build_dir / "bin" / "llama-server"
            if not llama_server.exists():
                llama_server = build_dir / "llama-server"
            if llama_server.exists():
                status["built"] = True
                status["server_available"] = True
                status["installed"] = True

    # Check if ccache is installed
    status["ccache_installed"] = shutil.which("ccache") is not None

    return status


@router.get("/llama-install")
async def install_llama_cpp():
    """Stream the installation process of llama.cpp."""

    async def generate():
        try:
            # Step 1: Clone repository
            if not LLAMA_CPP_DIR.exists():
                yield "data: [STEP] Cloning llama.cpp repository...\n\n"
                process = await asyncio.create_subprocess_exec(
                    "git", "clone", "https://github.com/ggml-org/llama.cpp",
                    cwd=str(PROJECT_ROOT),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                async for line in process.stdout:
                    yield f"data: {line.decode().strip()}\n\n"
                await process.wait()
                if process.returncode != 0:
                    yield "data: [ERROR] Failed to clone llama.cpp repository\n\n"
                    return
                yield "data: [SUCCESS] Repository cloned successfully\n\n"
            else:
                yield "data: [INFO] llama.cpp already cloned, skipping...\n\n"

            # Step 2: Check/install Homebrew (macOS package manager)
            if not shutil.which("brew"):
                yield "data: [STEP] Installing Homebrew package manager...\n\n"
                process = await asyncio.create_subprocess_shell(
                    '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    stdin=asyncio.subprocess.DEVNULL
                )
                async for line in process.stdout:
                    yield f"data: {line.decode().strip()}\n\n"
                await process.wait()
                if process.returncode != 0:
                    yield "data: [ERROR] Failed to install Homebrew. Please install manually from https://brew.sh\n\n"
                    return
                yield "data: [SUCCESS] Homebrew installed successfully\n\n"
            else:
                yield "data: [INFO] Homebrew already installed\n\n"

            # Step 3: Check/install ccache
            if not shutil.which("ccache"):
                yield "data: [STEP] Installing ccache for faster compilation...\n\n"
                process = await asyncio.create_subprocess_exec(
                    "brew", "install", "ccache",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                async for line in process.stdout:
                    yield f"data: {line.decode().strip()}\n\n"
                await process.wait()
            else:
                yield "data: [INFO] ccache already installed\n\n"

            # Step 4: Check/install cmake
            if not shutil.which("cmake"):
                yield "data: [STEP] Installing cmake...\n\n"
                process = await asyncio.create_subprocess_exec(
                    "brew", "install", "cmake",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                async for line in process.stdout:
                    yield f"data: {line.decode().strip()}\n\n"
                await process.wait()
                if process.returncode != 0:
                    yield "data: [ERROR] Failed to install cmake\n\n"
                    return
                yield "data: [SUCCESS] cmake installed successfully\n\n"
            else:
                yield "data: [INFO] cmake already installed\n\n"

            # Step 5: Configure with cmake
            yield "data: [STEP] Configuring build with cmake...\n\n"
            process = await asyncio.create_subprocess_exec(
                "cmake", "-B", "build",
                cwd=str(LLAMA_CPP_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            async for line in process.stdout:
                yield f"data: {line.decode().strip()}\n\n"
            await process.wait()
            if process.returncode != 0:
                yield "data: [ERROR] cmake configuration failed\n\n"
                return
            yield "data: [SUCCESS] cmake configuration complete\n\n"

            # Step 6: Build
            yield "data: [STEP] Building llama.cpp (this may take several minutes)...\n\n"
            process = await asyncio.create_subprocess_exec(
                "cmake", "--build", "build", "--config", "Release", "-j", "8",
                cwd=str(LLAMA_CPP_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            async for line in process.stdout:
                yield f"data: {line.decode().strip()}\n\n"
            await process.wait()
            if process.returncode != 0:
                yield "data: [ERROR] Build failed\n\n"
                return
            yield "data: [SUCCESS] Build complete!\n\n"

            yield "data: [COMPLETE] llama.cpp installation finished successfully!\n\n"

        except Exception as e:
            yield f"data: [ERROR] Installation failed: {str(e)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/llama-start-server")
async def start_llama_server():
    """Start the llama.cpp server with the specified model."""

    async def generate():
        try:
            yield "data: [STEP] Starting llama-server with gpt-oss-20b model...\n\n"
            yield "data: [INFO] This is a large model file and may take several minutes to download on first run.\n\n"

            # Find llama-server binary
            llama_server = LLAMA_CPP_DIR / "build" / "bin" / "llama-server"
            if not llama_server.exists():
                llama_server = LLAMA_CPP_DIR / "build" / "llama-server"

            if not llama_server.exists():
                yield "data: [ERROR] llama-server binary not found. Please build llama.cpp first.\n\n"
                return

            # Start the server
            process = await asyncio.create_subprocess_exec(
                str(llama_server),
                "-hf", "unsloth/gpt-oss-20b-GGUF",
                "--jinja", "-c", "4096", "-ngl", "99", "-fa", "on", "--n-cpu-moe", "4",
                "--host", "127.0.0.1",
                "--port", "8033",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            # Stream output for a while to show progress
            timeout = 120  # 2 minutes of streaming
            start_time = asyncio.get_event_loop().time()

            async for line in process.stdout:
                decoded = line.decode().strip()
                yield f"data: {decoded}\n\n"

                # Check if server is ready
                if "server listening" in decoded.lower() or "model loaded" in decoded.lower():
                    yield "data: [SUCCESS] Server is ready!\n\n"
                    yield "data: [COMPLETE] Local LLM server started on http://127.0.0.1:8033\n\n"
                    return

                # Timeout check
                if asyncio.get_event_loop().time() - start_time > timeout:
                    yield "data: [INFO] Server is still loading in the background...\n\n"
                    break

            yield "data: [INFO] Server process started. It may take a few more minutes to fully load the model.\n\n"

        except Exception as e:
            yield f"data: [ERROR] Failed to start server: {str(e)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


MODEL_CONFIGS = {
    "gpt-oss": {
        "name": "GPT-OSS-20B",
        "repo": "unsloth/gpt-oss-20b-GGUF",
        "size": "~13.8GB",
        "server_args": ["-hf", "unsloth/gpt-oss-20b-GGUF", "--jinja", "-c", "4096", "-ngl", "99", "-fa", "on", "--n-cpu-moe", "4"]
    },
    "qwen3": {
        "name": "Qwen3-8B",
        "repo": "Qwen/Qwen3-8B-GGUF",
        "filename": "Qwen3-8B-Q8_0.gguf",
        "size": "~8.5GB",
        "server_args": ["-hf", "Qwen/Qwen3-8B-GGUF", "--jinja", "-c", "0"]
    }
}


@router.get("/model-download")
async def download_model(model: str = "gpt-oss"):
    """Download a model using huggingface-cli."""

    if model not in MODEL_CONFIGS:
        async def error_gen():
            yield f"data: [ERROR] Unknown model: {model}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    config = MODEL_CONFIGS[model]

    async def generate():
        try:
            yield f"data: [STEP] Starting {config['name']} download...\n\n"
            yield f"data: [INFO] Downloading {config['repo']} ({config['size']}). This may take a while.\n\n"

            # Check if huggingface-cli is available
            if not shutil.which("huggingface-cli"):
                yield "data: [STEP] Installing huggingface-cli...\n\n"
                process = await asyncio.create_subprocess_exec(
                    "pip", "install", "-U", "huggingface_hub[cli]",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                async for line in process.stdout:
                    yield f"data: {line.decode().strip()}\n\n"
                await process.wait()
                if process.returncode != 0:
                    yield "data: [ERROR] Failed to install huggingface-cli\n\n"
                    return
                yield "data: [SUCCESS] huggingface-cli installed\n\n"

            # Download the model using huggingface-cli
            yield "data: [STEP] Downloading model from Hugging Face...\n\n"

            # Create models directory if it doesn't exist
            models_dir = PROJECT_ROOT / "models"
            models_dir.mkdir(exist_ok=True)

            model_dir_name = config['repo'].replace('/', '-')

            # Build command - download specific file if filename is specified
            cmd = [
                "huggingface-cli", "download",
                config['repo'],
            ]

            # Add specific filename if specified (downloads only that file)
            if 'filename' in config:
                cmd.append(config['filename'])
                yield f"data: [INFO] Downloading specific file: {config['filename']}\n\n"

            cmd.extend([
                "--local-dir", str(models_dir / model_dir_name),
                "--local-dir-use-symlinks", "False",
            ])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            async for line in process.stdout:
                decoded = line.decode().strip()
                if decoded:
                    yield f"data: {decoded}\n\n"

            await process.wait()

            if process.returncode != 0:
                yield "data: [ERROR] Model download failed\n\n"
                return

            yield f"data: [SUCCESS] {config['name']} downloaded successfully!\n\n"
            yield f"data: [COMPLETE] {config['name']} model is ready for use.\n\n"

        except Exception as e:
            yield f"data: [ERROR] Download failed: {str(e)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/start-local-server")
async def start_local_server(model: str = "gpt-oss"):
    """Start the local llama-server with the selected model."""

    if model not in MODEL_CONFIGS:
        async def error_gen():
            yield f"data: [ERROR] Unknown model: {model}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    config = MODEL_CONFIGS[model]

    async def generate():
        try:
            yield f"data: [STEP] Starting llama-server with {config['name']}...\n\n"

            # Find llama-server binary
            llama_server = LLAMA_CPP_DIR / "build" / "bin" / "llama-server"
            if not llama_server.exists():
                llama_server = LLAMA_CPP_DIR / "build" / "llama-server"

            if not llama_server.exists():
                yield "data: [ERROR] llama-server binary not found. Please install llama.cpp first.\n\n"
                return

            # Build server command
            cmd = [str(llama_server)] + config['server_args'] + ["--host", "127.0.0.1", "--port", "8033"]

            yield f"data: [INFO] Running: {' '.join(cmd)}\n\n"

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            # Stream output until server is ready or timeout
            timeout = 300  # 5 minutes for model loading
            start_time = asyncio.get_event_loop().time()

            async for line in process.stdout:
                decoded = line.decode().strip()
                yield f"data: {decoded}\n\n"

                # Check if server is ready
                if "server listening" in decoded.lower() or "model loaded" in decoded.lower() or "http server listening" in decoded.lower():
                    yield "data: [SUCCESS] Server is ready!\n\n"
                    yield "data: [COMPLETE] Local LLM server started on http://127.0.0.1:8033\n\n"
                    return

                # Timeout check
                if asyncio.get_event_loop().time() - start_time > timeout:
                    yield "data: [INFO] Server is still loading in the background...\n\n"
                    break

            yield "data: [INFO] Server process started. It may take a few more minutes to fully load the model.\n\n"

        except Exception as e:
            yield f"data: [ERROR] Failed to start server: {str(e)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
