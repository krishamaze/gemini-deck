"""
Gemini API Client for Gemini Command Deck.
Uses the official google.genai SDK (2026 recommended version).
Supports multi-account rotation with automatic 429 handling.
"""
from google import genai
from google.genai import types
from typing import AsyncIterator, Optional, List
import asyncio
import os

# Default model
DEFAULT_MODEL = "gemini-2.0-flash"


class GeminiAPIClient:
    """
    Gemini API client using google.genai SDK.
    Automatically handles streaming and quota errors.
    """
    
    def __init__(self, api_key: str = None, model: str = DEFAULT_MODEL):
        """Initialize with a specific API key or use environment variable."""
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model
        self._client = None
        
        if self.api_key:
            self._client = genai.Client(api_key=self.api_key)
    
    def configure(self, api_key: str):
        """Configure with a new API key."""
        self.api_key = api_key
        self._client = genai.Client(api_key=api_key)
    
    async def generate(self, prompt: str, context: List[str] = None) -> str:
        """
        Generate a response to a prompt.
        
        Args:
            prompt: The user's prompt
            context: Optional list of previous context strings
            
        Returns:
            The generated text response
        """
        if not self._client:
            raise ValueError("No API key configured. Call configure() or set GEMINI_API_KEY.")
        
        # Build full prompt with context
        full_prompt = prompt
        if context:
            context_str = "\n".join(context[-5:])  # Last 5 context items
            full_prompt = f"Previous context:\n{context_str}\n\nUser: {prompt}"
        
        try:
            # Run in thread pool since SDK may be sync
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt
                )
            )
            return response.text
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "rate" in error_str or "resource_exhausted" in error_str:
                raise QuotaExceededError(str(e))
            raise
    
    async def stream(self, prompt: str, context: List[str] = None) -> AsyncIterator[str]:
        """
        Stream a response to a prompt.
        
        Args:
            prompt: The user's prompt
            context: Optional list of previous context strings
            
        Yields:
            Text chunks as they arrive
        """
        if not self._client:
            raise ValueError("No API key configured. Call configure() or set GEMINI_API_KEY.")
        
        # Build full prompt with context
        full_prompt = prompt
        if context:
            context_str = "\n".join(context[-5:])
            full_prompt = f"Previous context:\n{context_str}\n\nUser: {prompt}"
        
        try:
            # Use streaming API
            loop = asyncio.get_event_loop()
            
            # Get stream in executor
            def get_stream():
                return self._client.models.generate_content_stream(
                    model=self.model_name,
                    contents=full_prompt
                )
            
            stream = await loop.run_in_executor(None, get_stream)
            
            # Iterate through stream
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "rate" in error_str or "resource_exhausted" in error_str:
                raise QuotaExceededError(str(e))
            raise


class QuotaExceededError(Exception):
    """Raised when API quota is exceeded (429 error)."""
    pass


class MultiAccountGeminiClient:
    """
    Gemini client with automatic multi-account rotation.
    When one account hits quota, automatically switches to another.
    """
    
    def __init__(self, user_id: int):
        """Initialize for a specific user."""
        self.user_id = user_id
        self._client = GeminiAPIClient()
        self._current_account_id = None
    
    async def _get_next_account(self):
        """Get the next available account with quota."""
        from app.routers.accounts import get_best_account
        
        account = get_best_account(self.user_id)
        if not account:
            raise ValueError("No AI accounts with available quota. Add more accounts or wait for quota reset.")
        
        self._current_account_id = account["id"]
        api_key = account.get("api_key") or account.get("token")
        
        if not api_key:
            raise ValueError(f"Account {account['name']} has no API key configured.")
        
        self._client.configure(api_key)
        return account
    
    async def _on_quota_exceeded(self):
        """Handle quota exceeded by switching accounts."""
        from app.routers.accounts import mark_account_error
        
        if self._current_account_id:
            mark_account_error(self._current_account_id, "429")
        
        # Try to get another account
        return await self._get_next_account()
    
    async def _on_success(self):
        """Record successful API call."""
        from app.routers.accounts import increment_usage
        
        if self._current_account_id:
            increment_usage(self._current_account_id)
    
    async def generate(self, prompt: str, context: List[str] = None, max_retries: int = 3) -> str:
        """
        Generate with automatic account rotation on 429.
        """
        if not self._current_account_id:
            await self._get_next_account()
        
        for attempt in range(max_retries):
            try:
                result = await self._client.generate(prompt, context)
                await self._on_success()
                return result
            except QuotaExceededError:
                if attempt < max_retries - 1:
                    await self._on_quota_exceeded()
                else:
                    raise
            except Exception:
                raise
        
        raise ValueError("Max retries exceeded")
    
    async def stream(self, prompt: str, context: List[str] = None, max_retries: int = 3) -> AsyncIterator[str]:
        """
        Stream with automatic account rotation on 429.
        """
        if not self._current_account_id:
            await self._get_next_account()
        
        for attempt in range(max_retries):
            try:
                async for chunk in self._client.stream(prompt, context):
                    yield chunk
                await self._on_success()
                return
            except QuotaExceededError:
                if attempt < max_retries - 1:
                    await self._on_quota_exceeded()
                else:
                    raise
            except Exception:
                raise


# Singleton for simple use cases (uses GEMINI_API_KEY env var)
_default_client = None

def get_default_client() -> GeminiAPIClient:
    """Get the default client using GEMINI_API_KEY environment variable."""
    global _default_client
    if _default_client is None:
        _default_client = GeminiAPIClient()
    return _default_client


# Export for backward compatibility
gemini_client = get_default_client()
