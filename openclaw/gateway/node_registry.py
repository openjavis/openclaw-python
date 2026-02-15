"""
Node registry for managing connected nodes and their subscriptions.

This module tracks nodes (external systems that connect to the gateway)
and manages their event subscriptions for targeted event delivery.

Nodes are different from regular clients - they typically represent:
- External services
- Mobile devices
- IoT devices
- Integration systems

Matches openclaw node registry system.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeEntry:
    """Registered node information"""
    
    nodeId: str
    connId: str  # WebSocket connection ID
    deviceId: str
    capabilities: list[str] = field(default_factory=list)
    subscriptions: dict[str, list[str]] = field(default_factory=dict)  # event_type -> [subscription_ids]
    connected_at: float = field(default_factory=time.time)
    last_ping_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class NodeRegistry:
    """
    Registry of connected nodes with subscription management.
    
    This registry tracks:
    - Connected nodes and their metadata
    - Node capabilities
    - Event subscriptions for targeted delivery
    - Connection health (ping tracking)
    
    Usage:
        registry = NodeRegistry()
        
        # Register node
        registry.register_node(
            node_id="node_123",
            conn_id="conn_456",
            device_id="device_789",
            capabilities=["execute", "approve"]
        )
        
        # Subscribe to events
        registry.subscribe(
            node_id="node_123",
            event_type="exec.approval.requested",
            subscription_id="sub_001"
        )
        
        # Get subscribers for event
        subscribers = registry.get_subscribers("exec.approval.requested")
        
        # Update ping
        registry.update_ping("node_123")
        
        # Unregister on disconnect
        registry.unregister_node("node_123")
    """
    
    def __init__(self):
        """Initialize node registry"""
        self._nodes: dict[str, NodeEntry] = {}  # nodeId -> NodeEntry
        self._conn_to_node: dict[str, str] = {}  # connId -> nodeId
        self._device_to_nodes: dict[str, set[str]] = {}  # deviceId -> {nodeIds}
    
    def register_node(
        self, 
        node_id: str, 
        conn_id: str, 
        device_id: str, 
        capabilities: list[str] | None = None,
        metadata: dict[str, Any] | None = None
    ) -> NodeEntry:
        """
        Register connected node.
        
        Args:
            node_id: Unique node ID
            conn_id: WebSocket connection ID
            device_id: Device ID
            capabilities: Node capabilities
            metadata: Additional metadata
            
        Returns:
            Registered node entry
        """
        node = NodeEntry(
            nodeId=node_id,
            connId=conn_id,
            deviceId=device_id,
            capabilities=capabilities or [],
            subscriptions={},
            connected_at=time.time(),
            last_ping_at=time.time(),
            metadata=metadata or {}
        )
        
        self._nodes[node_id] = node
        self._conn_to_node[conn_id] = node_id
        
        # Track device -> nodes mapping
        if device_id not in self._device_to_nodes:
            self._device_to_nodes[device_id] = set()
        self._device_to_nodes[device_id].add(node_id)
        
        return node
    
    def unregister_node(self, node_id: str) -> NodeEntry | None:
        """
        Unregister node on disconnect.
        
        Args:
            node_id: Node ID to unregister
            
        Returns:
            Unregistered node entry if found, None otherwise
        """
        node = self._nodes.pop(node_id, None)
        if node:
            self._conn_to_node.pop(node.connId, None)
            
            # Remove from device mapping
            device_nodes = self._device_to_nodes.get(node.deviceId)
            if device_nodes:
                device_nodes.discard(node_id)
                if not device_nodes:
                    del self._device_to_nodes[node.deviceId]
        
        return node
    
    def get_node(self, node_id: str) -> NodeEntry | None:
        """
        Get node by ID.
        
        Args:
            node_id: Node ID
            
        Returns:
            Node entry if found, None otherwise
        """
        return self._nodes.get(node_id)
    
    def get_node_by_conn(self, conn_id: str) -> NodeEntry | None:
        """
        Get node by connection ID.
        
        Args:
            conn_id: Connection ID
            
        Returns:
            Node entry if found, None otherwise
        """
        node_id = self._conn_to_node.get(conn_id)
        return self._nodes.get(node_id) if node_id else None
    
    def get_nodes_by_device(self, device_id: str) -> list[NodeEntry]:
        """
        Get all nodes for a device.
        
        Args:
            device_id: Device ID
            
        Returns:
            List of node entries for device
        """
        node_ids = self._device_to_nodes.get(device_id, set())
        return [self._nodes[node_id] for node_id in node_ids if node_id in self._nodes]
    
    def subscribe(
        self, 
        node_id: str, 
        event_type: str, 
        subscription_id: str
    ) -> bool:
        """
        Subscribe node to event type.
        
        Args:
            node_id: Node ID
            event_type: Event type to subscribe to
            subscription_id: Unique subscription ID
            
        Returns:
            True if subscribed successfully, False if node not found
        """
        node = self._nodes.get(node_id)
        if not node:
            return False
        
        if event_type not in node.subscriptions:
            node.subscriptions[event_type] = []
        
        if subscription_id not in node.subscriptions[event_type]:
            node.subscriptions[event_type].append(subscription_id)
        
        return True
    
    def unsubscribe(
        self, 
        node_id: str, 
        event_type: str, 
        subscription_id: str | None = None
    ) -> bool:
        """
        Unsubscribe node from event type.
        
        Args:
            node_id: Node ID
            event_type: Event type to unsubscribe from
            subscription_id: Specific subscription ID, or None to remove all
            
        Returns:
            True if unsubscribed, False if node not found
        """
        node = self._nodes.get(node_id)
        if not node:
            return False
        
        if event_type not in node.subscriptions:
            return False
        
        if subscription_id:
            # Remove specific subscription
            try:
                node.subscriptions[event_type].remove(subscription_id)
            except ValueError:
                pass
            
            # Remove event type if no more subscriptions
            if not node.subscriptions[event_type]:
                del node.subscriptions[event_type]
        else:
            # Remove all subscriptions for event type
            del node.subscriptions[event_type]
        
        return True
    
    def get_subscribers(self, event_type: str) -> list[NodeEntry]:
        """
        Get nodes subscribed to event type.
        
        Args:
            event_type: Event type
            
        Returns:
            List of subscribed node entries
        """
        return [
            node for node in self._nodes.values()
            if event_type in node.subscriptions
        ]
    
    def update_ping(self, node_id: str) -> bool:
        """
        Update last ping time for node.
        
        Args:
            node_id: Node ID
            
        Returns:
            True if updated, False if node not found
        """
        node = self._nodes.get(node_id)
        if node:
            node.last_ping_at = time.time()
            return True
        return False
    
    def list_nodes(self) -> list[NodeEntry]:
        """
        List all registered nodes.
        
        Returns:
            List of all node entries
        """
        return list(self._nodes.values())
    
    def list_nodes_by_capability(self, capability: str) -> list[NodeEntry]:
        """
        List nodes with specific capability.
        
        Args:
            capability: Capability to filter by
            
        Returns:
            List of nodes with capability
        """
        return [
            node for node in self._nodes.values()
            if capability in node.capabilities
        ]
    
    def count(self) -> int:
        """Get number of registered nodes"""
        return len(self._nodes)
    
    def clear(self) -> None:
        """Clear all nodes (for testing/reset)"""
        self._nodes.clear()
        self._conn_to_node.clear()
        self._device_to_nodes.clear()


__all__ = [
    "NodeEntry",
    "NodeRegistry",
]
