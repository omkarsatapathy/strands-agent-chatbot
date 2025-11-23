"""Morning brief generator that captures streaming agent outputs and creates audio briefing."""
import asyncio
import os
import sys
import subprocess
import time
import signal
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import requests

# Add parent directory to path for imports when run directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from strands import Agent
from src.config import Config
from src.logging_config import get_logger
from src.agent.streaming_agent import create_streaming_response
from src.agent.model_providers import ModelProviderFactory
from src.voice import get_voice_generator
from src.utils.token_tracker import TokenTracker

logger = get_logger("chatbot.morning_brief")


class ServerManager:
    """Manage backend and llama server lifecycle."""

    BACKEND_PORT = 8000
    LLAMA_PORT = 8033
    BACKEND_PATH = "/Users/omkarsatapaphy/python_works/agentic_chatbot/backend.py"
    CONDA_ENV = "ai_env"

    @staticmethod
    def check_port(port: int) -> bool:
        """
        Check if a server is running on the specified port.

        Args:
            port: Port number to check

        Returns:
            True if server is responding, False otherwise
        """
        import socket
        try:
            # Try to connect to the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result == 0
        except Exception:
            return False

    @staticmethod
    def kill_port(port: int) -> bool:
        """
        Kill any process running on the specified port.

        Args:
            port: Port number to kill

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"🔪 Killing processes on port {port}...")
            result = subprocess.run(
                f"lsof -ti:{port} | xargs kill -9 2>/dev/null",
                shell=True,
                capture_output=True,
                text=True
            )
            time.sleep(1)
            return True
        except Exception as e:
            logger.warning(f"⚠️ Could not kill port {port}: {e}")
            return False

    @staticmethod
    def start_llama_server() -> Optional[subprocess.Popen]:
        """
        Start llama-server if not already running.

        Returns:
            Popen process object or None if already running
        """
        if ServerManager.check_port(ServerManager.LLAMA_PORT):
            logger.info(f"✅ Llama server already running on port {ServerManager.LLAMA_PORT}")
            return None

        logger.info("🚀 Starting llama-server...")
        try:
            # Start llama server in background
            process = subprocess.Popen(
                [
                    "llama-server",
                    "-hf", "unsloth/gpt-oss-20b-GGUF",
                    "--jinja",
                    "-c", "4096", "-ngl", "99", "-fa", "on", "--n-cpu-moe", "4",
                    "--host", "127.0.0.1",
                    "--port", str(ServerManager.LLAMA_PORT)
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )

            # Wait for server to start
            max_wait = 30
            for i in range(max_wait):
                if ServerManager.check_port(ServerManager.LLAMA_PORT):
                    logger.info(f"✅ Llama server started successfully on port {ServerManager.LLAMA_PORT}")
                    return process
                time.sleep(1)
                logger.info(f"⏳ Waiting for llama server... ({i+1}/{max_wait}s)")

            logger.error("❌ Llama server failed to start within timeout")
            process.kill()
            return None

        except Exception as e:
            logger.error(f"❌ Failed to start llama server: {e}")
            return None

    @staticmethod
    def start_backend_server() -> Optional[subprocess.Popen]:
        """
        Start backend server if not already running.

        Returns:
            Popen process object or None if already running
        """
        if ServerManager.check_port(ServerManager.BACKEND_PORT):
            logger.info(f"✅ Backend server already running on port {ServerManager.BACKEND_PORT}")
            return None

        logger.info("🚀 Starting backend server...")
        try:
            # Kill existing processes on port
            ServerManager.kill_port(ServerManager.BACKEND_PORT)

            # Start backend server
            bash_command = f"""
            eval "$(conda shell.bash hook)" &&
            conda activate {ServerManager.CONDA_ENV} &&
            python {ServerManager.BACKEND_PATH}
            """

            process = subprocess.Popen(
                bash_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                executable="/bin/bash",
                preexec_fn=os.setsid  # Create new process group
            )

            # Wait for server to start
            max_wait = 20
            for i in range(max_wait):
                if ServerManager.check_port(ServerManager.BACKEND_PORT):
                    logger.info(f"✅ Backend server started successfully on port {ServerManager.BACKEND_PORT}")
                    return process
                time.sleep(1)
                logger.info(f"⏳ Waiting for backend server... ({i+1}/{max_wait}s)")

            logger.error("❌ Backend server failed to start within timeout")
            process.kill()
            return None

        except Exception as e:
            logger.error(f"❌ Failed to start backend server: {e}")
            return None

    @staticmethod
    def ensure_servers_running() -> tuple[Optional[subprocess.Popen], Optional[subprocess.Popen]]:
        """
        Ensure both servers are running, starting them if necessary.

        Returns:
            Tuple of (llama_process, backend_process) - None if already running
        """
        logger.info("🔍 Checking server status...")

        # Start llama server
        llama_process = ServerManager.start_llama_server()

        # Start backend server
        backend_process = ServerManager.start_backend_server()

        if not ServerManager.check_port(ServerManager.LLAMA_PORT):
            raise Exception("Llama server is not running and could not be started")

        if not ServerManager.check_port(ServerManager.BACKEND_PORT):
            raise Exception("Backend server is not running and could not be started")

        logger.info("✅ All servers are running")
        return llama_process, backend_process

    @staticmethod
    def cleanup_processes(llama_process: Optional[subprocess.Popen],
                         backend_process: Optional[subprocess.Popen]):
        """
        Clean up server processes if they were started by this script.

        Args:
            llama_process: Llama server process to kill
            backend_process: Backend server process to kill
        """
        if llama_process:
            logger.info("🛑 Stopping llama server...")
            try:
                os.killpg(os.getpgid(llama_process.pid), signal.SIGTERM)
                llama_process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"⚠️ Error stopping llama server: {e}")

        if backend_process:
            logger.info("🛑 Stopping backend server...")
            try:
                os.killpg(os.getpgid(backend_process.pid), signal.SIGTERM)
                backend_process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"⚠️ Error stopping backend server: {e}")


class MorningBriefGenerator:
    """Generate morning briefings from multiple agent queries."""

    def __init__(self):
        """Initialize the morning brief generator."""
        self.output_dir = Path("/Users/omkarsatapaphy/Desktop/morning_brief")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tracker = TokenTracker()

    async def capture_agent_response(self, prompt: str) -> str:
        """
        Capture the complete response from streaming agent.

        Args:
            prompt: The prompt to send to the agent

        Returns:
            Complete response text
        """
        logger.info(f"📝 Capturing response for: {prompt}")
        complete_response = ""

        # Stream the agent response
        async for event_line in create_streaming_response(
            message=prompt,
            conversation_history=[],
            session_id=None,
            model_provider="llamacpp"
        ):
            # Parse SSE format: "event: type\ndata: json_data\n\n"
            if event_line.startswith("data: "):
                import json
                try:
                    data_str = event_line[6:]  # Remove "data: " prefix
                    data = json.loads(data_str)

                    # Capture the final response from done event
                    if "response" in data:
                        complete_response = data["response"]
                        logger.info(f"✅ Captured complete response ({len(complete_response)} chars)")

                        # Track token usage
                        if "tokens" in data:
                            usage_dict = {
                                "prompt_tokens": data["tokens"]["input"],
                                "completion_tokens": data["tokens"]["output"]
                            }
                            # Use gpt-4o since that's what the openai provider uses
                            self.tracker.add_completion_usage(usage_dict, "gpt-4o")

                except json.JSONDecodeError:
                    pass

        return complete_response

    async def generate_morning_brief(self) -> tuple[str, str, str]:
        """
        Generate morning brief by executing predefined prompts.

        Returns:
            Tuple of (audio_path, text_path, cost_info)
        """
        logger.info("🌅 Starting morning brief generation")

        # Define the prompts
        prompts = [
            "Summarize and give me an email briefing for this morning in a story fashion.",
            "What are the news updates on Stock market and what is today's forecast?",
            "Plan a productive day for me as I am a AI developer based in Hyderabad India. also learning new skills on the side.",
            "Tell me what is the latest updates on technology and AI advancements news?",
            "What are the weather updates for Hyderabad India this morning?"
        ]

        # Capture all responses
        responses = []
        for i, prompt in enumerate(prompts, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Query {i}/{len(prompts)}: {prompt}")
            logger.info(f"{'='*60}")

            response = await self.capture_agent_response(prompt)
            responses.append(response)

            logger.info(f"✅ Query {i} completed\n")

        # Create summary brief using Strands agent
        logger.info("📋 Creating summary briefing...")
        summary_brief = await self._create_summary_brief(responses)

        # Generate audio file
        logger.info("🎵 Generating audio briefing...")
        audio_path = await self._generate_audio(summary_brief)

        # Save text and cost files
        text_path = await self._save_text_brief(summary_brief, responses)
        cost_path = await self._save_cost_report()

        logger.info("✅ Morning brief generation completed!")
        logger.info(f"📁 Audio file: {audio_path}")
        logger.info(f"📁 Text file: {text_path}")
        logger.info(f"📁 Cost report: {cost_path}")

        return audio_path, text_path, cost_path

    async def _create_summary_brief(self, responses: List[str]) -> str:
        """
        Create a summarized morning brief from all responses using Strands agent.

        Args:
            responses: List of response strings from queries

        Returns:
            Summarized morning brief
        """
        # Initialize OpenAI model
        provider = ModelProviderFactory.create_provider("llamacpp")
        model = provider.get_model()

        # Create a summarization agent
        summary_agent = Agent(
            name="Morning Brief Summarizer",
            model=model,
            system_prompt="""You are a professional news anchor creating a morning briefing.
Your job is to take multiple information sources and create a cohesive, engaging morning brief.

Guidelines:
- Start with a warm greeting
- Present information in a natural, flowing narrative
- Organize by topic (emails, stock market, weather)
- Keep it concise but informative
- End with an uplifting note
- Write in a conversational tone suitable for audio playback
- Maximum 700 words"""
        )

        # Combine responses into prompt
        combined_info = "\n\n=== EMAIL BRIEFING ===\n" + responses[0]
        combined_info += "\n\n=== STOCK MARKET NEWS ===\n" + responses[1]
        combined_info += "\n\n=== WEATHER UPDATE ===\n" + responses[2]

        prompt = f"""Create a morning news brief from the following information:

{combined_info}

Please create a cohesive, engaging morning briefing suitable for audio playback."""

        # Run the agent using stream_async and collect the response
        summary = ""
        async for event in summary_agent.stream_async(prompt):
            event_type = event.get("type")

            # Collect text chunks
            if "data" in event:
                summary += event["data"]

            # Track token usage from result
            elif event_type == "result":
                result = event.get("result")
                if result and hasattr(result, 'usage') and result.usage:
                    usage_dict = {
                        "prompt_tokens": getattr(result.usage, 'input_tokens', 0),
                        "completion_tokens": getattr(result.usage, 'output_tokens', 0)
                    }
                    self.tracker.add_completion_usage(usage_dict, "gpt-4o")
        logger.info(f"✅ Summary created ({len(summary)} chars)")

        return summary

    async def _generate_audio(self, text: str) -> str:
        """
        Generate audio file from text using OpenAI TTS.

        Args:
            text: Text to convert to speech

        Returns:
            Path to saved audio file
        """
        voice_gen = get_voice_generator()

        # Generate audio
        audio_bytes = voice_gen.generate_speech(text, response_format="wav")

        if not audio_bytes:
            raise Exception("Failed to generate audio")

        # Track TTS usage
        self.tracker.add_tts_usage(text, voice_gen.model)

        # Save to file with date
        date_str = datetime.now().strftime("%d_%b_%Y")
        audio_filename = f"{date_str}.wav"
        audio_path = self.output_dir / audio_filename

        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        logger.info(f"🎵 Audio saved: {audio_path}")
        return str(audio_path)

    async def _save_text_brief(self, summary: str, full_responses: List[str]) -> str:
        """
        Save text briefing to file.

        Args:
            summary: Summarized morning brief
            full_responses: List of full responses from queries

        Returns:
            Path to saved text file
        """
        date_str = datetime.now().strftime("%d_%b_%Y")
        text_filename = f"{date_str}_brief.txt"
        text_path = self.output_dir / text_filename

        with open(text_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write(f"MORNING BRIEF - {datetime.now().strftime('%B %d, %Y')}\n")
            f.write("=" * 70 + "\n\n")

            f.write("📻 AUDIO BRIEFING SCRIPT\n")
            f.write("-" * 70 + "\n")
            f.write(summary)
            f.write("\n\n")

            f.write("=" * 70 + "\n")
            f.write("📋 DETAILED REPORTS\n")
            f.write("=" * 70 + "\n\n")

            topics = ["EMAIL BRIEFING", "STOCK MARKET NEWS", "WEATHER UPDATE"]
            for topic, response in zip(topics, full_responses):
                f.write(f"\n{topic}\n")
                f.write("-" * 70 + "\n")
                f.write(response)
                f.write("\n\n")

        logger.info(f"📄 Text brief saved: {text_path}")
        return str(text_path)

    async def _save_cost_report(self) -> str:
        """
        Save cost report to file.

        Returns:
            Path to saved cost report file
        """
        date_str = datetime.now().strftime("%d_%b_%Y")
        cost_filename = f"{date_str}_cost.txt"
        cost_path = self.output_dir / cost_filename

        # Calculate costs
        cost_data = self.tracker.calculate_cost(
            model_id="gpt-4o",
            tts_model_id="tts-1"
        )

        with open(cost_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write(f"OPENAI USAGE COST REPORT - {datetime.now().strftime('%B %d, %Y')}\n")
            f.write("=" * 70 + "\n\n")

            f.write("TOKEN USAGE:\n")
            f.write("-" * 70 + "\n")
            f.write(f"Model:             {cost_data['model_id']}\n")
            f.write(f"Input Tokens:      {cost_data['input_tokens']:,}\n")
            f.write(f"Output Tokens:     {cost_data['output_tokens']:,}\n")
            f.write(f"Total Tokens:      {cost_data['total_tokens']:,}\n\n")

            f.write("TTS USAGE:\n")
            f.write("-" * 70 + "\n")
            f.write(f"Model:             {cost_data['tts_model_id']}\n")
            f.write(f"Characters:        {cost_data['tts_characters']:,}\n\n")

            f.write("COST BREAKDOWN:\n")
            f.write("-" * 70 + "\n")
            f.write(f"Input Cost:        ${cost_data['input_cost_usd']:.6f} USD  (₹{cost_data['input_cost_usd'] * TokenTracker.USD_TO_INR:.4f})\n")
            f.write(f"Output Cost:       ${cost_data['output_cost_usd']:.6f} USD  (₹{cost_data['output_cost_usd'] * TokenTracker.USD_TO_INR:.4f})\n")
            f.write(f"TTS Cost:          ${cost_data['tts_cost_usd']:.6f} USD  (₹{cost_data['tts_cost_usd'] * TokenTracker.USD_TO_INR:.4f})\n")
            f.write("-" * 70 + "\n")
            f.write(f"TOTAL COST:        ${cost_data['total_cost_usd']:.6f} USD  (₹{cost_data['total_cost_inr']:.4f})\n")
            f.write("=" * 70 + "\n")

        logger.info(f"💰 Cost report saved: {cost_path}")
        logger.info(f"💰 Total Cost: ${cost_data['total_cost_usd']:.6f} USD (₹{cost_data['total_cost_inr']:.4f})")

        return str(cost_path)


async def main(skip_server_check: bool = False):
    """
    Main entry point for morning brief generation.

    Args:
        skip_server_check: If True, skip server management (assumes servers are running)
    """
    llama_process = None
    backend_process = None

    try:
        # Ensure servers are running
        if not skip_server_check:
            llama_process, backend_process = ServerManager.ensure_servers_running()
        else:
            logger.info("⏭️ Skipping server checks (assuming servers are running)")

        # Generate morning brief
        generator = MorningBriefGenerator()
        audio_path, text_path, cost_path = await generator.generate_morning_brief()

        print("\n" + "=" * 70)
        print("🌅 MORNING BRIEF GENERATED SUCCESSFULLY!")
        print("=" * 70)
        print(f"🎵 Audio:  {audio_path}")
        print(f"📄 Text:   {text_path}")
        print(f"💰 Cost:   {cost_path}")
        print("=" * 70 + "\n")

    except KeyboardInterrupt:
        logger.info("\n⚠️ Process interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error generating morning brief: {e}", exc_info=True)
        raise
    finally:
        # Clean up servers if we started them
        if not skip_server_check:
            ServerManager.cleanup_processes(llama_process, backend_process)


if __name__ == "__main__":
    import sys
    skip_check = "--skip-server-check" in sys.argv
    asyncio.run(main(skip_server_check=skip_check))
