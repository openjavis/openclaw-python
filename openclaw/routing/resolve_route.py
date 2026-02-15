"""
Agent route resolution with binding matching.

Matches openclaw/src/routing/resolve-route.ts
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .session_key import (
    build_agent_session_key,
    build_agent_main_session_key,
    normalize_agent_id,
    normalize_account_id,
    DEFAULT_ACCOUNT_ID,
    DEFAULT_MAIN_KEY,
)


@dataclass
class RoutePeer:
    """Peer information for routing"""
    kind: Literal["dm", "group", "channel"]
    id: str


@dataclass
class ResolvedAgentRoute:
    """Resolved agent route"""
    agent_id: str
    channel: str
    account_id: str
    session_key: str
    main_session_key: str
    matched_by: Literal[
        "binding.peer",
        "binding.peer.parent",
        "binding.guild",
        "binding.team",
        "binding.account",
        "binding.channel",
        "default"
    ]


def normalize_token(value: str | None) -> str:
    """Normalize string token to lowercase"""
    return (value or "").strip().lower()


def normalize_id(value: str | None) -> str:
    """Normalize ID (preserve case)"""
    return (value or "").strip()


def matches_account_id(match: str | None, actual: str) -> bool:
    """Check if account ID matches"""
    trimmed = (match or "").strip()
    if not trimmed:
        return actual == DEFAULT_ACCOUNT_ID
    if trimmed == "*":
        return True
    return trimmed == actual


def matches_channel(binding: dict, channel: str) -> bool:
    """Check if binding matches channel"""
    match = binding.get("match", {})
    key = normalize_token(match.get("channel"))
    if not key:
        return False
    return key == channel


def matches_peer(binding: dict, peer: RoutePeer) -> bool:
    """Check if binding matches peer"""
    match = binding.get("match", {})
    peer_match = match.get("peer")
    if not peer_match:
        return False
    
    kind = normalize_token(peer_match.get("kind"))
    peer_id = normalize_id(peer_match.get("id"))
    
    if not kind or not peer_id:
        return False
    
    return kind == peer.kind and peer_id == peer.id


def matches_guild(binding: dict, guild_id: str) -> bool:
    """Check if binding matches guild"""
    match = binding.get("match", {})
    match_guild_id = normalize_id(match.get("guildId"))
    if not match_guild_id:
        return False
    return match_guild_id == guild_id


def matches_team(binding: dict, team_id: str) -> bool:
    """Check if binding matches team"""
    match = binding.get("match", {})
    match_team_id = normalize_id(match.get("teamId"))
    if not match_team_id:
        return False
    return match_team_id == team_id


def list_bindings(config) -> list[dict]:
    """
    List all bindings from config.
    
    Args:
        config: OpenClaw configuration
        
    Returns:
        List of binding objects
    """
    # Access bindings from config
    if hasattr(config, 'session') and hasattr(config.session, 'bindings'):
        bindings = config.session.bindings
        if isinstance(bindings, list):
            return bindings
    
    # Fallback: try dict access
    if isinstance(config, dict):
        session = config.get('session', {})
        bindings = session.get('bindings', [])
        if isinstance(bindings, list):
            return bindings
    
    return []


def resolve_default_agent_id(config) -> str:
    """
    Resolve default agent ID from config.
    
    Args:
        config: OpenClaw configuration
        
    Returns:
        Default agent ID
    """
    # Try to get default agent from config
    if hasattr(config, 'agents') and hasattr(config.agents, 'default'):
        return config.agents.default or "main"
    
    # Try dict access
    if isinstance(config, dict):
        agents = config.get('agents', {})
        return agents.get('default', 'main')
    
    return "main"


def list_agents(config) -> list[dict]:
    """List all agents from config"""
    if hasattr(config, 'agents') and hasattr(config.agents, 'list'):
        agents = config.agents.list
        if isinstance(agents, list):
            return agents
    
    if isinstance(config, dict):
        agents = config.get('agents', {})
        agent_list = agents.get('list', [])
        if isinstance(agent_list, list):
            return agent_list
    
    return []


def pick_first_existing_agent_id(config, agent_id: str) -> str:
    """
    Pick first existing agent ID, fallback to default.
    
    Args:
        config: OpenClaw configuration
        agent_id: Requested agent ID
        
    Returns:
        Resolved agent ID
    """
    trimmed = (agent_id or "").strip()
    if not trimmed:
        return normalize_agent_id(resolve_default_agent_id(config))
    
    normalized = normalize_agent_id(trimmed)
    agents = list_agents(config)
    
    if not agents:
        return normalize_agent_id(trimmed)
    
    # Find matching agent
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        agent_id_str = agent.get('id', '')
        if normalize_agent_id(agent_id_str) == normalized:
            return normalize_agent_id(agent_id_str)
    
    # Fallback to default
    return normalize_agent_id(resolve_default_agent_id(config))


def resolve_agent_route(
    config,
    channel: str,
    account_id: str | None = None,
    peer: RoutePeer | dict | None = None,
    parent_peer: RoutePeer | dict | None = None,
    guild_id: str | None = None,
    team_id: str | None = None
) -> ResolvedAgentRoute:
    """
    Resolve agent and session key via binding hierarchy.
    
    Matching order:
    1. Peer binding (exact peer ID match)
    2. Parent peer binding (for threads)
    3. Guild binding (for group/channel peers)
    4. Team binding (Slack workspace)
    5. Account binding (channel account)
    6. Channel binding (any account wildcard)
    7. Default agent
    
    Args:
        config: OpenClaw configuration
        channel: Channel name
        account_id: Account ID
        peer: Peer information (kind, id)
        parent_peer: Parent peer for thread inheritance
        guild_id: Guild ID (Discord)
        team_id: Team ID (Slack)
        
    Returns:
        ResolvedAgentRoute with agentId, sessionKey, matchedBy
    """
    channel_norm = normalize_token(channel)
    account_id_norm = normalize_account_id(account_id)
    
    # Normalize peer
    if peer:
        if isinstance(peer, dict):
            peer = RoutePeer(
                kind=peer.get("kind", "dm"),
                id=normalize_id(peer.get("id", ""))
            )
        else:
            peer = RoutePeer(
                kind=peer.kind,
                id=normalize_id(peer.id)
            )
    
    # Normalize parent peer
    if parent_peer:
        if isinstance(parent_peer, dict):
            parent_peer = RoutePeer(
                kind=parent_peer.get("kind", "dm"),
                id=normalize_id(parent_peer.get("id", ""))
            )
        else:
            parent_peer = RoutePeer(
                kind=parent_peer.kind,
                id=normalize_id(parent_peer.id)
            )
    
    guild_id_norm = normalize_id(guild_id) if guild_id else None
    team_id_norm = normalize_id(team_id) if team_id else None
    
    # Filter bindings by channel and account
    all_bindings = list_bindings(config)
    bindings = []
    for binding in all_bindings:
        if not binding or not isinstance(binding, dict):
            continue
        if not matches_channel(binding, channel_norm):
            continue
        match = binding.get("match", {})
        if not matches_account_id(match.get("accountId"), account_id_norm):
            continue
        bindings.append(binding)
    
    # Get dmScope and identity links from config
    dm_scope = "main"
    identity_links = None
    
    if hasattr(config, 'session'):
        if hasattr(config.session, 'dmScope'):
            dm_scope = config.session.dmScope or "main"
        if hasattr(config.session, 'identityLinks'):
            identity_links = config.session.identityLinks
    elif isinstance(config, dict):
        session = config.get('session', {})
        dm_scope = session.get('dmScope', 'main')
        identity_links = session.get('identityLinks')
    
    def choose(agent_id: str, matched_by: str) -> ResolvedAgentRoute:
        """Build resolved route"""
        resolved_agent_id = pick_first_existing_agent_id(config, agent_id)
        
        session_key = build_agent_session_key(
            agent_id=resolved_agent_id,
            channel=channel_norm,
            account_id=account_id_norm,
            peer={"kind": peer.kind, "id": peer.id} if peer else None,
            dm_scope=dm_scope,
            identity_links=identity_links
        ).lower()
        
        main_session_key = build_agent_main_session_key(
            agent_id=resolved_agent_id,
            main_key=DEFAULT_MAIN_KEY
        ).lower()
        
        return ResolvedAgentRoute(
            agent_id=resolved_agent_id,
            channel=channel_norm,
            account_id=account_id_norm,
            session_key=session_key,
            main_session_key=main_session_key,
            matched_by=matched_by
        )
    
    # 1. Try peer binding
    if peer:
        for binding in bindings:
            if matches_peer(binding, peer):
                return choose(binding.get("agentId", "main"), "binding.peer")
    
    # 2. Try parent peer binding (thread inheritance)
    if parent_peer and parent_peer.id:
        for binding in bindings:
            if matches_peer(binding, parent_peer):
                return choose(binding.get("agentId", "main"), "binding.peer.parent")
    
    # 3. Try guild binding
    if guild_id_norm:
        for binding in bindings:
            if matches_guild(binding, guild_id_norm):
                return choose(binding.get("agentId", "main"), "binding.guild")
    
    # 4. Try team binding
    if team_id_norm:
        for binding in bindings:
            if matches_team(binding, team_id_norm):
                return choose(binding.get("agentId", "main"), "binding.team")
    
    # 5. Try account binding (specific account, no peer/guild/team)
    for binding in bindings:
        match = binding.get("match", {})
        account_id_match = (match.get("accountId") or "").strip()
        if account_id_match != "*" and not match.get("peer") and not match.get("guildId") and not match.get("teamId"):
            return choose(binding.get("agentId", "main"), "binding.account")
    
    # 6. Try channel binding (any account wildcard)
    for binding in bindings:
        match = binding.get("match", {})
        account_id_match = (match.get("accountId") or "").strip()
        if account_id_match == "*" and not match.get("peer") and not match.get("guildId") and not match.get("teamId"):
            return choose(binding.get("agentId", "main"), "binding.channel")
    
    # 7. Default
    return choose(resolve_default_agent_id(config), "default")


__all__ = [
    "RoutePeer",
    "ResolvedAgentRoute",
    "resolve_agent_route",
]
