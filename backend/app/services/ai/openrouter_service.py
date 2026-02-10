"""
OpenRouter AI service layer.

Provides unified interface for all AI-powered endpoints using OpenRouter as the gateway.
Handles authentication, request formatting, response parsing, and error handling.
Tracks token usage for subscription billing.

CRITICAL: This service is EXPLANATION-ONLY. It never modifies invoice data,
XML structure, tax values, hashes, signatures, or any ZATCA-critical operations.
"""

import logging
from typing import Dict, Optional, Any
import httpx
import json

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OpenRouterService:
    """
    OpenRouter AI service for unified AI gateway access.
    
    Provides a single method to call OpenRouter with proper authentication,
    error handling, and token usage tracking.
    """
    
    def __init__(self):
        """Initializes OpenRouter service with configuration."""
        settings = get_settings()
        
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url.rstrip("/")
        self.default_model = settings.openrouter_default_model
        self.timeout = settings.openrouter_timeout
        
        # CRITICAL: Check if OpenRouter is configured
        if not self.api_key:
            logger.warning("OpenRouter API key not configured. AI services will not work.")
            self.client = None
        else:
            # Initialize httpx client with timeout
            self.client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://zatca-api.com",  # Your app URL
                    "X-Title": "ZATCA Compliance API"  # Your app name
                }
            )
    
    async def call_openrouter(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Calls OpenRouter API with the provided prompt.
        
        CRITICAL: This method only generates AI responses. It does NOT modify
        invoice data, XML, tax values, hashes, or signatures.
        
        Args:
            prompt: User prompt/message
            model: Model to use (defaults to configured default model)
            system_prompt: Optional system prompt for context
            temperature: Temperature for response (default: 0.3)
            max_tokens: Maximum tokens in response (default: 2000)
            response_format: Optional response format (e.g., {"type": "json_object"})
            
        Returns:
            Dictionary containing:
                - content: AI response content
                - usage: Token usage information (prompt_tokens, completion_tokens, total_tokens)
                - model: Model used for the response
                
        Raises:
            ValueError: If OpenRouter is not configured or request fails
            httpx.TimeoutException: If request times out
        """
        if not self.client:
            raise ValueError("OpenRouter is not configured. Please set OPENROUTER_API_KEY.")
        
        # Use default model if not specified
        model = model or self.default_model
        
        # Build messages array
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Build request payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Add response format if specified
        if response_format:
            payload["response_format"] = response_format
        
        try:
            # Make request to OpenRouter
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            
            # Extract content
            choices = response_data.get("choices", [])
            if not choices:
                raise ValueError("OpenRouter returned empty response")
            
            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise ValueError("OpenRouter returned empty content")
            
            # Extract usage information
            usage = response_data.get("usage", {})
            token_usage = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
            
            # Extract model used
            model_used = response_data.get("model", model)
            
            logger.debug(
                f"OpenRouter API call successful: model={model_used}, "
                f"tokens={token_usage['total_tokens']}"
            )
            
            return {
                "content": content,
                "usage": token_usage,
                "model": model_used
            }
            
        except httpx.TimeoutException as e:
            logger.error(f"OpenRouter API timeout: {e}")
            raise ValueError(f"AI service timeout: Request took longer than {self.timeout} seconds")
        
        except httpx.HTTPStatusError as e:
            error_detail = "Unknown error"
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error", {}).get("message", str(e))
            except:
                error_detail = str(e)
            
            logger.error(f"OpenRouter API error: {e.response.status_code} - {error_detail}")
            raise ValueError(f"AI service error: {error_detail}")
        
        except httpx.RequestError as e:
            logger.error(f"OpenRouter request error: {e}")
            raise ValueError(f"AI service connection error: {str(e)}")
        
        except json.JSONDecodeError as e:
            logger.error(f"OpenRouter response parsing error: {e}")
            raise ValueError("AI service returned invalid response format")
        
        except Exception as e:
            logger.error(f"Unexpected OpenRouter error: {e}")
            raise ValueError(f"AI service error: {str(e)}")
    
    async def close(self):
        """Closes the HTTP client (for cleanup)."""
        if self.client:
            await self.client.aclose()


# Singleton instance
_openrouter_service: Optional[OpenRouterService] = None


def get_openrouter_service() -> OpenRouterService:
    """
    Returns singleton OpenRouter service instance.
    
    Returns:
        OpenRouterService instance
    """
    global _openrouter_service
    if _openrouter_service is None:
        _openrouter_service = OpenRouterService()
    return _openrouter_service

