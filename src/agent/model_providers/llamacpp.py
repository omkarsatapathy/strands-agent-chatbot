"""LlamaCpp model provider implementations for different models."""
import subprocess
import time
import requests
import os
import signal
import json
from pathlib import Path
from strands.models.llamacpp import LlamaCppModel
from .base import BaseModelProvider
from ...config import Config
from ...logging_config import get_logger

logger = get_logger("chatbot.model_providers.llamacpp")


class DebugLlamaCppModel(LlamaCppModel):
    """LlamaCppModel with request debugging and better error handling."""

    def _format_request(self, messages, tool_specs=None, system_prompt=None):
        """Override to log the formatted request."""
        request = super()._format_request(messages, tool_specs, system_prompt)
        logger.info(f"🔍 LlamaCpp Request (messages count: {len(request.get('messages', []))})")
        # Log the messages for debugging
        try:
            for i, msg in enumerate(request.get('messages', [])):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                tool_calls = msg.get('tool_calls', [])
                tool_call_id = msg.get('tool_call_id', '')

                content_preview = str(content)[:100] if content else '(empty)'
                logger.info(f"  Message {i}: role={role}, content={content_preview}, tool_calls={len(tool_calls)}, tool_call_id={tool_call_id}")

                # Log full message if it has tool role (to debug 400 error)
                if role == 'tool':
                    logger.info(f"    FULL TOOL MESSAGE: {json.dumps(msg)[:500]}")

                # Log assistant messages with tool_calls
                if role == 'assistant' and tool_calls:
                    logger.info(f"    ASSISTANT TOOL_CALLS: {json.dumps(tool_calls)[:500]}")

            # Log total payload size for debugging context overflow
            payload_size = len(json.dumps(request))
            logger.info(f"📏 Total request payload size: {payload_size:,} bytes")

            # Log tool specs count
            if tool_specs:
                logger.info(f"🔧 Tool specs count: {len(tool_specs)}")

            # If payload is large, dump full request to file for debugging
            if payload_size > 10000:
                debug_file = "/tmp/llamacpp_debug_request.json"
                with open(debug_file, 'w') as f:
                    json.dump(request, f, indent=2)
                logger.info(f"📝 Full request dumped to {debug_file}")
        except Exception as e:
            logger.error(f"Failed to log request details: {e}")
        return request

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        """Override stream to add better error handling for 400 errors."""
        import httpx
        try:
            async for event in super().stream(messages, tool_specs, system_prompt, **kwargs):
                yield event
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                # Log the full error response for debugging
                try:
                    error_body = e.response.text
                    logger.error(f"❌ LlamaCpp 400 Error Response: {error_body[:500]}")
                except Exception:
                    pass
                # Re-raise with more context
                raise RuntimeError(
                    f"LlamaCpp server returned 400 Bad Request. "
                    f"This usually means the message format is incompatible with the model's chat template. "
                    f"Error: {str(e)}"
                ) from e
            raise

# Global server process tracking
_server_process = None
_current_model = None


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.parent


def get_llama_server_path() -> Path:
    """Get path to llama-server binary."""
    return get_project_root() / "llama.cpp" / "build" / "bin" / "llama-server"


def get_model_path(model_name: str) -> Path:
    """Get path to model file based on model name."""
    project_root = get_project_root()

    if model_name == "gpt-oss":
        # GPT-OSS-20B model path - check both possible locations
        new_path = project_root / "models" / "ggml-org-gpt-oss-20b-GGUF" / "gpt-oss-20b-mxfp4.gguf"
        old_path = project_root / "models" / "gpt-oss-20B-v2.2.Q6_K.gguf"
        if new_path.exists():
            return new_path
        return old_path
    elif model_name == "qwen3":
        # Qwen3-8B model path - check both possible locations
        new_path = project_root / "models" / "Qwen-Qwen3-8B-GGUF" / "Qwen3-8B-Q8_0.gguf"
        hf_path = project_root / "models" / "Qwen-Qwen3-8B-GGUF"
        if new_path.exists():
            return new_path
        # Check for any gguf file in the directory
        if hf_path.exists():
            for f in hf_path.glob("*.gguf"):
                return f
        return new_path
    else:
        raise ValueError(f"Unknown model: {model_name}")


def is_server_running(port: int = 8033) -> bool:
    """Check if llama-server is running on the specified port."""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def stop_server():
    """Stop the currently running llama-server."""
    global _server_process, _current_model

    if _server_process is not None:
        logger.info(f"Stopping llama-server (model: {_current_model})")
        try:
            _server_process.terminate()
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.kill()
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
        finally:
            _server_process = None
            _current_model = None


def start_server(model_name: str, port: int = 8033, ctx_size: int = 4096, n_gpu_layers: int = 99, n_cpu_moe: int = 4) -> bool:
    """
    Start llama-server with the specified model.

    Args:
        model_name: Name of the model ('gpt-oss' or 'qwen3')
        port: Port to run the server on
        ctx_size: Context size for the model
        n_gpu_layers: Number of GPU layers to offload
        n_cpu_moe: Number of MoE layers to keep on CPU (for Mac memory limits)

    Returns:
        True if server started successfully, False otherwise
    """
    global _server_process, _current_model

    # If server is already running with the same model, return True
    if _current_model == model_name and is_server_running(port):
        logger.info(f"Server already running with model: {model_name}")
        return True

    # Stop any existing server
    stop_server()

    # Get paths
    server_path = get_llama_server_path()
    model_path = get_model_path(model_name)

    # Verify paths exist
    if not server_path.exists():
        logger.error(f"llama-server not found at: {server_path}")
        return False

    if not model_path.exists():
        logger.error(f"Model not found at: {model_path}")
        return False

    # Build command
    # --jinja flag is required for tool/function calling support
    cmd = [
        str(server_path),
        "-m", str(model_path),
        "--port", str(port),
        "-c", str(ctx_size),
        "-ngl", str(n_gpu_layers),
        "-fa", "on",  # Flash attention
        "--n-cpu-moe", str(n_cpu_moe),  # Keep MoE layers on CPU for Mac
        "--host", "127.0.0.1",
        "--jinja"
    ]

    logger.info(f"Starting llama-server with model: {model_name}")
    logger.info(f"Command: {' '.join(cmd)}")

    try:
        # Start server process
        _server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        _current_model = model_name

        # Wait for server to be ready
        max_wait = 60  # seconds
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if is_server_running(port):
                logger.info(f"✅ llama-server started successfully with {model_name}")
                return True

            # Check if process died
            if _server_process.poll() is not None:
                stdout, stderr = _server_process.communicate()
                logger.error(f"Server process died: {stderr.decode()}")
                _server_process = None
                _current_model = None
                return False

            time.sleep(1)

        logger.error("Server startup timeout")
        stop_server()
        return False

    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        _server_process = None
        _current_model = None
        return False


class LlamaCppGptOssProvider(BaseModelProvider):
    """Provider for LlamaCpp with GPT-OSS-20B model."""

    def __init__(self):
        """Initialize LlamaCpp GPT-OSS provider."""
        self.base_url = Config.LLAMA_CPP_URL
        self.max_tokens = Config.LLM_MAX_TOKENS
        self.temperature = Config.LLM_TEMPERATURE
        self.model_name = "gpt-oss"
        self.model_id = "gpt-oss-20b"

    def get_model(self) -> LlamaCppModel:
        """
        Get LlamaCpp model instance after ensuring server is running.

        Returns:
            Initialized LlamaCppModel
        """
        # Ensure server is running with the correct model
        if not start_server(self.model_name):
            raise RuntimeError(f"Failed to start llama-server with {self.model_name}")

        return DebugLlamaCppModel(
            base_url=self.base_url,
            model_id=self.model_id,
            timeout=120.0,  # Increased timeout for large models
            params={
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "repeat_penalty": 1.1,
            }
        )

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "llamacpp-gpt-oss"

    def is_available(self) -> bool:
        """
        Check if LlamaCpp GPT-OSS is available.

        Returns:
            True if server binary and model exist
        """
        server_exists = get_llama_server_path().exists()
        try:
            model_exists = get_model_path(self.model_name).exists()
        except ValueError:
            model_exists = False

        return server_exists and model_exists


class LlamaCppQwen3Provider(BaseModelProvider):
    """Provider for LlamaCpp with Qwen3-8B model."""

    def __init__(self):
        """Initialize LlamaCpp Qwen3 provider."""
        self.base_url = Config.LLAMA_CPP_URL
        self.max_tokens = Config.LLM_MAX_TOKENS
        self.temperature = Config.LLM_TEMPERATURE
        self.model_name = "qwen3"
        self.model_id = "qwen3-8b"

    def get_model(self) -> LlamaCppModel:
        """
        Get LlamaCpp model instance after ensuring server is running.

        Returns:
            Initialized LlamaCppModel
        """
        # Ensure server is running with the correct model
        if not start_server(self.model_name):
            raise RuntimeError(f"Failed to start llama-server with {self.model_name}")

        return LlamaCppModel(
            base_url=self.base_url,
            model_id=self.model_id,
            timeout=120.0,  # Increased timeout for large models
            params={
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "repeat_penalty": 1.1,
            }
        )

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "llamacpp-qwen3"

    def is_available(self) -> bool:
        """
        Check if LlamaCpp Qwen3 is available.

        Returns:
            True if server binary and model exist
        """
        server_exists = get_llama_server_path().exists()
        try:
            model_exists = get_model_path(self.model_name).exists()
        except ValueError:
            model_exists = False

        return server_exists and model_exists


# Keep backward compatibility with original provider
class LlamaCppProvider(LlamaCppQwen3Provider):
    """Default LlamaCpp provider (uses Qwen3-8B)."""
    pass
