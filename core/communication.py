import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from collections import defaultdict
import threading

from governance.audit_log import log_event
from governance.zero_trust import sign_payload, verify_payload

MESSAGES_DIR = "messages"

class Message:
    def __init__(
        self,
        sender: str,
        receiver: str,
        message_type: str,
        content: Any,
        metadata: Dict = None
    ):
        self.message_id = str(uuid.uuid4())
        self.sender = sender
        self.receiver = receiver
        self.message_type = message_type
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()
        self.signature = None
    
    def to_dict(self) -> Dict:
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "signature": self.signature
        }
    
    def _signing_payload(self) -> Dict:
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }
    
    def sign(self):
        payload = self._signing_payload()
        self.signature = sign_payload(payload)
        return self
    
    def verify(self) -> bool:
        if not self.signature:
            return False
        payload = self._signing_payload()
        return verify_payload(payload, self.signature)


class MessageBus:
    def __init__(self):
        self.messages_dir = Path(MESSAGES_DIR)
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        
        self.inboxes = defaultdict(list)
        self.message_log = []
        self.lock = threading.Lock()
        
        self.subscribers = defaultdict(list)
    
    def send_message(self, message: Message, sign: bool = True) -> str:
        if sign:
            message.sign()
        
        with self.lock:
            self.inboxes[message.receiver].append(message)
            self.message_log.append(message)
            
            self._persist_message(message)
            
            log_event(
                "message_sent",
                message.sender,
                "inter_agent_communication",
                {
                    "message_id": message.message_id,
                    "receiver": message.receiver,
                    "type": message.message_type
                }
            )
            
            self._notify_subscribers(message)
        
        return message.message_id
    
    def receive_messages(self, agent_name: str, limit: int = 10) -> List[Message]:
        with self.lock:
            messages = self.inboxes[agent_name][:limit]
            self.inboxes[agent_name] = self.inboxes[agent_name][limit:]
            return messages
    
    def peek_messages(self, agent_name: str, limit: int = 10) -> List[Message]:
        with self.lock:
            return self.inboxes[agent_name][:limit]
    
    def broadcast(self, sender: str, message_type: str, content: Any, metadata: Dict = None):
        agents = ["autobot", "alpha_evaluator", "beta_worker"]
        
        for agent in agents:
            if agent != sender:
                message = Message(sender, agent, message_type, content, metadata)
                self.send_message(message)
    
    def subscribe(self, agent_name: str, callback):
        self.subscribers[agent_name].append(callback)
    
    def _notify_subscribers(self, message: Message):
        for callback in self.subscribers[message.receiver]:
            try:
                callback(message)
            except Exception as e:
                print(f"[COMMUNICATION] Subscriber callback error: {e}")
    
    def _persist_message(self, message: Message):
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        message_file = self.messages_dir / f"msg_{message.message_id}_{timestamp}.json"
        
        # Ensure directory exists before writing
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        
        with open(message_file, "w") as f:
            json.dump(message.to_dict(), f, indent=2)
    
    def get_message_log(self, agent_name: str = None, limit: int = 100) -> List[Dict]:
        with self.lock:
            if agent_name:
                messages = [m for m in self.message_log if m.sender == agent_name or m.receiver == agent_name]
            else:
                messages = self.message_log
            
            return [m.to_dict() for m in messages[-limit:]]
    
    def get_communication_stats(self) -> Dict[str, Any]:
        with self.lock:
            stats = {
                "total_messages": len(self.message_log),
                "messages_by_type": defaultdict(int),
                "messages_by_sender": defaultdict(int),
                "messages_by_receiver": defaultdict(int),
                "pending_messages": {agent: len(msgs) for agent, msgs in self.inboxes.items()}
            }
            
            for msg in self.message_log:
                stats["messages_by_type"][msg.message_type] += 1
                stats["messages_by_sender"][msg.sender] += 1
                stats["messages_by_receiver"][msg.receiver] += 1
            
            return stats


class AgentCommunication:
    def __init__(self, agent_name: str, message_bus: MessageBus):
        self.agent_name = agent_name
        self.message_bus = message_bus
        self.communication_history = []
    
    def send(self, receiver: str, message_type: str, content: Any, metadata: Dict = None) -> str:
        message = Message(self.agent_name, receiver, message_type, content, metadata)
        message_id = self.message_bus.send_message(message)
        
        self.communication_history.append({
            "direction": "sent",
            "message_id": message_id,
            "receiver": receiver,
            "type": message_type,
            "timestamp": message.timestamp
        })
        
        return message_id
    
    def receive(self, limit: int = 10) -> List[Message]:
        messages = self.message_bus.receive_messages(self.agent_name, limit)
        
        for msg in messages:
            self.communication_history.append({
                "direction": "received",
                "message_id": msg.message_id,
                "sender": msg.sender,
                "type": msg.message_type,
                "timestamp": msg.timestamp
            })
        
        return messages
    
    def broadcast(self, message_type: str, content: Any, metadata: Dict = None):
        self.message_bus.broadcast(self.agent_name, message_type, content, metadata)
    
    def get_pending_count(self) -> int:
        messages = self.message_bus.peek_messages(self.agent_name)
        return len(messages)
    
    def get_communication_history(self, limit: int = 50) -> List[Dict]:
        return self.communication_history[-limit:]


_message_bus = None

def get_message_bus() -> MessageBus:
    global _message_bus
    if _message_bus is None:
        _message_bus = MessageBus()
    return _message_bus

def get_agent_communication(agent_name: str) -> AgentCommunication:
    bus = get_message_bus()
    return AgentCommunication(agent_name, bus)

def send_message(sender: str, receiver: str, message_type: str, content: Any, metadata: Dict = None) -> str:
    comm = get_agent_communication(sender)
    return comm.send(receiver, message_type, content, metadata)

def receive_messages(agent_name: str, limit: int = 10) -> List[Message]:
    comm = get_agent_communication(agent_name)
    return comm.receive(limit)

def broadcast_message(sender: str, message_type: str, content: Any, metadata: Dict = None):
    comm = get_agent_communication(sender)
    comm.broadcast(message_type, content, metadata)

def get_communication_stats() -> Dict[str, Any]:
    bus = get_message_bus()
    return bus.get_communication_stats()

def get_message_log(agent_name: str = None, limit: int = 100) -> List[Dict]:
    bus = get_message_bus()
    return bus.get_message_log(agent_name, limit)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Inter-agent communication system")
    parser.add_argument("--stats", action="store_true", help="Show communication statistics")
    parser.add_argument("--log", action="store_true", help="Show message log")
    parser.add_argument("--agent", help="Filter by agent name")
    parser.add_argument("--limit", type=int, default=100, help="Limit results")
    
    args = parser.parse_args()
    
    if args.stats:
        stats = get_communication_stats()
        print(json.dumps(stats, indent=2))
    elif args.log:
        log = get_message_log(args.agent, args.limit)
        print(json.dumps(log, indent=2))
    else:
        parser.print_help()
