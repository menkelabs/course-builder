"""
Registration Client for Embabel Server.

Handles registering this Python agent with an Embabel server
so it can participate in GOAP planning and action execution.
"""

import logging
from typing import Optional, Dict, Any
import asyncio

import httpx

from .models import ServerRegistration

logger = logging.getLogger(__name__)


class EmbabelClient:
    """
    Client for registering with and communicating with an Embabel server.
    
    Usage:
        client = EmbabelClient(
            embabel_url="http://localhost:8080",
            agent_url="http://localhost:8000",
            agent_name="python-agent",
            agent_description="Python tools for course building",
        )
        await client.register()
    """
    
    def __init__(
        self,
        embabel_url: str,
        agent_url: str,
        agent_name: str = "python-agent",
        agent_description: str = "Python-based tools for the Course Builder pipeline",
        timeout: float = 30.0,
    ):
        """
        Initialize the Embabel client.
        
        Args:
            embabel_url: Base URL of the Embabel server
            agent_url: Base URL of this Python agent
            agent_name: Name to register as
            agent_description: Description of this agent
            timeout: Request timeout in seconds
        """
        self.embabel_url = embabel_url.rstrip("/")
        self.agent_url = agent_url.rstrip("/")
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.timeout = timeout
        
        self._client: Optional[httpx.AsyncClient] = None
        self._registered = False
    
    @property
    def registration(self) -> ServerRegistration:
        """Get the server registration payload."""
        return ServerRegistration(
            base_url=self.agent_url,
            name=self.agent_name,
            description=self.agent_description,
        )
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def register(self) -> bool:
        """
        Register this agent with the Embabel server.
        
        Returns:
            True if registration was successful
        
        Raises:
            httpx.HTTPError: If registration fails
        """
        client = await self._get_client()
        
        url = f"{self.embabel_url}/api/v1/remote/register"
        payload = self.registration.to_dict()
        
        logger.info(f"Registering with Embabel server at {url}")
        logger.debug(f"Registration payload: {payload}")
        
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            self._registered = True
            logger.info(f"Successfully registered as '{self.agent_name}'")
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Registration failed: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Registration request failed: {e}")
            raise
    
    async def health_check(self) -> bool:
        """
        Check if the Embabel server is reachable.
        
        Returns:
            True if server is healthy
        """
        client = await self._get_client()
        
        try:
            response = await client.get(f"{self.embabel_url}/health")
            return response.status_code == 200
        except httpx.RequestError:
            return False
    
    async def list_remote_actions(self) -> Dict[str, Any]:
        """
        List all remote actions registered on the Embabel server.
        
        Returns:
            List of remote action metadata
        """
        client = await self._get_client()
        
        url = f"{self.embabel_url}/api/v1/remote"
        response = await client.get(url)
        response.raise_for_status()
        
        return response.json()


async def register_with_embabel(
    embabel_url: str,
    agent_url: str,
    agent_name: str = "python-agent",
    agent_description: str = "Python-based tools for the Course Builder pipeline",
    retry_count: int = 3,
    retry_delay: float = 2.0,
) -> bool:
    """
    Register this agent with an Embabel server with retries.
    
    Args:
        embabel_url: Embabel server URL
        agent_url: This agent's URL
        agent_name: Agent name
        agent_description: Agent description
        retry_count: Number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        True if registration was successful
    """
    client = EmbabelClient(
        embabel_url=embabel_url,
        agent_url=agent_url,
        agent_name=agent_name,
        agent_description=agent_description,
    )
    
    try:
        for attempt in range(retry_count):
            try:
                return await client.register()
            except Exception as e:
                if attempt < retry_count - 1:
                    logger.warning(
                        f"Registration attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    raise
        return False
    finally:
        await client.close()
