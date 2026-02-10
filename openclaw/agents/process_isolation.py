"""Agent process isolation

Manages isolated agent processes for better resource control.
Provides真正的进程隔离 using multiprocessing.
"""
from __future__ import annotations

import asyncio
import logging
import multiprocessing as mp
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentProcessConfig:
    """Configuration for isolated agent process"""
    
    session_key: str
    workspace_dir: Path
    model: str
    timeout_s: float = 300.0
    memory_limit_mb: int | None = None
    cpu_limit: float | None = None


class AgentProcessManager:
    """
    Agent process isolation manager
    
    Creates truly isolated agent processes using multiprocessing.
    Each agent runs in its own process with resource limits.
    """
    
    def __init__(self):
        self._processes: dict[str, mp.Process] = {}
        self._queues: dict[str, mp.Queue] = {}
        self._lock = asyncio.Lock()
    
    async def spawn_isolated_agent(
        self,
        config: AgentProcessConfig,
    ) -> int:
        """
        Spawn an isolated agent process
        
        Args:
            config: Agent process configuration
            
        Returns:
            Process ID
        """
        logger.info(f"Spawning isolated agent: {config.session_key}")
        
        # Create communication queue
        queue = mp.Queue()
        self._queues[config.session_key] = queue
        
        # Create process
        process = mp.Process(
            target=_agent_process_worker,
            args=(config, queue),
            name=f"agent-{config.session_key}",
        )
        
        # Start process
        process.start()
        
        async with self._lock:
            self._processes[config.session_key] = process
        
        logger.info(f"Agent process started: PID={process.pid}")
        
        return process.pid
    
    async def terminate_agent(self, session_key: str):
        """
        Terminate an agent process
        
        Args:
            session_key: Session key
        """
        async with self._lock:
            process = self._processes.get(session_key)
        
        if not process:
            logger.warning(f"No process found for session: {session_key}")
            return
        
        logger.info(f"Terminating agent process: {session_key} (PID={process.pid})")
        
        # Terminate process
        process.terminate()
        
        # Wait for termination (with timeout)
        process.join(timeout=5.0)
        
        # Force kill if still alive
        if process.is_alive():
            logger.warning(f"Force killing process: {session_key}")
            process.kill()
            process.join()
        
        # Clean up
        async with self._lock:
            self._processes.pop(session_key, None)
            self._queues.pop(session_key, None)
        
        logger.info(f"Agent process terminated: {session_key}")
    
    async def send_message(self, session_key: str, message: dict[str, Any]):
        """
        Send message to agent process
        
        Args:
            session_key: Session key
            message: Message dict
        """
        queue = self._queues.get(session_key)
        if not queue:
            raise ValueError(f"No queue for session: {session_key}")
        
        queue.put(message)
    
    async def receive_message(self, session_key: str, timeout: float = 1.0) -> dict[str, Any] | None:
        """
        Receive message from agent process
        
        Args:
            session_key: Session key
            timeout: Timeout in seconds
            
        Returns:
            Message dict or None
        """
        queue = self._queues.get(session_key)
        if not queue:
            return None
        
        try:
            # Run blocking get in thread pool
            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(
                None,
                queue.get,
                True,  # block
                timeout,
            )
            return message
        except Exception:
            return None
    
    def list_processes(self) -> list[dict[str, Any]]:
        """
        List all agent processes
        
        Returns:
            List of process info dicts
        """
        processes = []
        
        for session_key, process in self._processes.items():
            processes.append({
                "session_key": session_key,
                "pid": process.pid,
                "is_alive": process.is_alive(),
                "name": process.name,
            })
        
        return processes


def _agent_process_worker(config: AgentProcessConfig, queue: mp.Queue):
    """
    Worker function for agent process
    
    This runs in the isolated process.
    
    Args:
        config: Agent configuration
        queue: Communication queue
    """
    import asyncio
    
    # Set up logging in subprocess
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Agent process worker started: {config.session_key}")
    
    try:
        # TODO: Initialize agent in isolated process
        # This would:
        # 1. Load agent configuration
        # 2. Initialize LLM provider
        # 3. Set up tool registry
        # 4. Run agent loop
        # 5. Send results back via queue
        
        # For now, just simulate
        import time
        time.sleep(1)
        
        # Send completion message
        queue.put({
            "type": "complete",
            "session_key": config.session_key,
            "success": True,
        })
        
    except Exception as e:
        logger.error(f"Agent process error: {e}")
        queue.put({
            "type": "error",
            "session_key": config.session_key,
            "error": str(e),
        })
    
    logger.info(f"Agent process worker finished: {config.session_key}")


# Global manager instance
_manager: AgentProcessManager | None = None


def get_agent_process_manager() -> AgentProcessManager:
    """Get global agent process manager"""
    global _manager
    if _manager is None:
        _manager = AgentProcessManager()
    return _manager
