import asyncio
import json
import subprocess
from typing import AsyncGenerator

class GeminiClient:
    def __init__(self):
        self.command = ["gemini", "--headless"]

    async def generate_text(self, prompt: str, context: list = None) -> str:
        """
        Executes Gemini CLI and returns the full response text.
        """
        full_prompt = prompt
        if context:
            context_str = "\n".join([f"- {m.get('user_prompt', '')} -> {m.get('ai_response', '')}" for m in context])
            full_prompt = f"Context from past interactions:\n{context_str}\n\nUser Query: {prompt}"

        proc = await asyncio.create_subprocess_exec(
            *self.command, "--prompt", full_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise Exception(f"Gemini CLI Error: {stderr.decode()}")

        # Parse JSONL output to reconstruct full text
        full_text = ""
        for line in stdout.decode().splitlines():
            try:
                data = json.loads(line)
                full_text += data.get("text", "")
            except:
                pass
                
        return full_text if full_text else stdout.decode()

    async def stream_chat(self, prompt: str, context: list = None) -> AsyncGenerator[str, None]:
        """
        Executes Gemini CLI and yields chunks of response.
        Context is prepended to the prompt if provided.
        """
        
        full_prompt = prompt
        if context:
            context_str = "\n".join([f"- {m.get('user_prompt', '')} -> {m.get('ai_response', '')}" for m in context])
            full_prompt = f"Context from past interactions:\n{context_str}\n\nUser Query: {prompt}"

        # We need to construct the input payload if the CLI supports JSON input, 
        # otherwise we pass via --prompt argument. 
        # To be safe with complex chars, we'll try to use stdin or just arg.
        # Given current knowledge of CLI, we use --prompt.
        
        proc = await asyncio.create_subprocess_exec(
            *self.command, "--prompt", full_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Read stdout line by line (assuming JSONL or text output)
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            
            decoded_line = line.decode().strip()
            if decoded_line:
                yield decoded_line

        await proc.wait()

gemini_client = GeminiClient()
