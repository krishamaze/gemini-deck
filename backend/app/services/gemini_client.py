import asyncio
import json
import subprocess
from typing import AsyncGenerator

class GeminiClient:
    def __init__(self):
        self.command = ["gemini", "--headless"]

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
