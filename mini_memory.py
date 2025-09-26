"""MEMORY dataclasses and data structures for CCN app."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Deque
from collections import deque
from datetime import datetime
import json


@dataclass
class SynapticKV:
    """Key-value pair for SYNAPTIC lists."""
    key: str
    value: Any
    
    def __post_init__(self):
        """Validate key format."""
        if not self.key.startswith(('attributes.', 'llm_config.')):
            raise ValueError(f"Invalid key '{self.key}': must start with 'attributes.' or 'llm_config.'")


@dataclass
class SynapticKVList:
    """List of SYNAPTIC key-value pairs."""
    kvs: List[SynapticKV] = field(default_factory=list)
    
    def add(self, key: str, value: Any) -> None:
        """Add a key-value pair."""
        self.kvs.append(SynapticKV(key=key, value=value))
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key."""
        for kv in self.kvs:
            if kv.key == key:
                return kv.value
        return default
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {kv.key: kv.value for kv in self.kvs}


@dataclass
class MaterializedRole:
    """Materialized role with attributes and LLM config."""
    node_id: str
    entry_id: str
    input_signals: List[str] = field(default_factory=list)
    node_output_signal: Optional[str] = None
    tasks: List[str] = field(default_factory=list)
    instructions: str = ""
    llm_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default LLM config if not provided."""
        if not self.llm_config:
            self.llm_config = {
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.1,
                "max_tokens": 4096,
                "reasoning_effort": "low",
                "response_format": {"type": "json_object"}
            }


@dataclass
class PerRoleRecord:
    """Record of a role execution."""
    node_id: str
    entry_id: str
    input_signals: List[str]
    node_output_signal: Optional[str]
    tasks: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "node_id": self.node_id,
            "entry_id": self.entry_id,
            "input_signals": self.input_signals,
            "node_output_signal": self.node_output_signal,
            "tasks": self.tasks,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error
        }


@dataclass
class CCNEvent:
    """CCN execution event."""
    event_type: str  # 'role_start', 'role_complete', 'error', 'prompt_window', 'memory_mutation'
    node_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type,
            "node_id": self.node_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }


@dataclass
class MEMORY:
    """Main MEMORY structure."""
    worklist: Deque[SynapticKVList] = field(default_factory=deque)
    active_slot: Optional[MaterializedRole] = None
    archive: List[PerRoleRecord] = field(default_factory=list)
    aggregator_buffer: List[Any] = field(default_factory=list)
    run_log: List[CCNEvent] = field(default_factory=list)
    
    def add_to_worklist(self, synaptic_list: SynapticKVList) -> None:
        """Add SYNAPTIC list to worklist."""
        self.worklist.append(synaptic_list)
    
    def pop_from_worklist(self) -> Optional[SynapticKVList]:
        """Pop from worklist."""
        if self.worklist:
            return self.worklist.popleft()
        return None
    
    def add_to_archive(self, record: PerRoleRecord) -> None:
        """Add record to archive."""
        self.archive.append(record)
    
    def add_to_aggregator(self, data: Any) -> None:
        """Add data to aggregator buffer."""
        self.aggregator_buffer.append(data)
    
    def log_event(self, event: CCNEvent) -> None:
        """Log CCN event."""
        self.run_log.append(event)
    
    def set_active_role(self, role: MaterializedRole) -> None:
        """Set active role in slot."""
        self.active_slot = role
    
    def clear_active_role(self) -> None:
        """Clear active role slot."""
        self.active_slot = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert MEMORY to dictionary for debugging."""
        return {
            "worklist_size": len(self.worklist),
            "active_slot": self.active_slot.__dict__ if self.active_slot else None,
            "archive_size": len(self.archive),
            "aggregator_buffer_size": len(self.aggregator_buffer),
            "run_log_size": len(self.run_log)
        }
