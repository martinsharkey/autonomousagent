import pytest
import json
import shutil
from pathlib import Path

from core.communication import (
    Message,
    MessageBus,
    AgentCommunication,
    get_message_bus,
    send_message,
    receive_messages,
    broadcast_message,
    get_communication_stats
)


class TestMessage:
    def test_message_creation(self):
        msg = Message(
            sender="autobot",
            receiver="alpha_evaluator",
            message_type="request",
            content={"task": "review code"}
        )
        
        assert msg.sender == "autobot"
        assert msg.receiver == "alpha_evaluator"
        assert msg.message_type == "request"
        assert msg.content["task"] == "review code"
        assert msg.message_id is not None
        assert msg.timestamp is not None
    
    def test_message_to_dict(self):
        msg = Message("autobot", "beta_worker", "info", {"data": "test"})
        msg_dict = msg.to_dict()
        
        assert msg_dict["sender"] == "autobot"
        assert msg_dict["receiver"] == "beta_worker"
        assert msg_dict["message_type"] == "info"
        assert msg_dict["content"]["data"] == "test"
    
    def test_message_signing(self):
        msg = Message("autobot", "beta_worker", "test", {"data": "value"})
        msg.sign()
        
        assert msg.signature is not None
        assert len(msg.signature) > 0
    
    def test_message_verification(self):
        msg = Message("autobot", "beta_worker", "test", {"data": "value"})
        msg.sign()
        
        assert msg.verify() is True
        
        msg.content["data"] = "tampered"
        assert msg.verify() is False


class TestMessageBus:
    def setup_method(self):
        self.bus = MessageBus()
        self.messages_dir = Path("messages")
        try:
            if self.messages_dir.exists():
                shutil.rmtree(self.messages_dir, ignore_errors=True)
        except Exception:
            pass
        self.messages_dir.mkdir(exist_ok=True)
    
    def teardown_method(self):
        try:
            if self.messages_dir.exists():
                shutil.rmtree(self.messages_dir, ignore_errors=True)
        except Exception:
            pass
    
    def test_send_message(self):
        msg = Message("autobot", "beta_worker", "test", {"data": "value"})
        message_id = self.bus.send_message(msg, sign=False)
        
        assert message_id == msg.message_id
        assert len(self.bus.inboxes["beta_worker"]) == 1
    
    def test_receive_messages(self):
        msg1 = Message("autobot", "beta_worker", "test1", {})
        msg2 = Message("alpha_evaluator", "beta_worker", "test2", {})
        
        self.bus.send_message(msg1, sign=False)
        self.bus.send_message(msg2, sign=False)
        
        received = self.bus.receive_messages("beta_worker", limit=10)
        assert len(received) == 2
        assert received[0].sender == "autobot"
        assert received[1].sender == "alpha_evaluator"
        
        received_again = self.bus.receive_messages("beta_worker")
        assert len(received_again) == 0
    
    def test_peek_messages(self):
        msg = Message("autobot", "beta_worker", "test", {})
        self.bus.send_message(msg, sign=False)
        
        peeked = self.bus.peek_messages("beta_worker")
        assert len(peeked) == 1
        
        still_there = self.bus.peek_messages("beta_worker")
        assert len(still_there) == 1
    
    def test_broadcast(self):
        self.bus.broadcast("autobot", "announcement", {"info": "test"})
        
        alpha_msgs = self.bus.receive_messages("alpha_evaluator")
        beta_msgs = self.bus.receive_messages("beta_worker")
        
        assert len(alpha_msgs) == 1
        assert len(beta_msgs) == 1
        assert alpha_msgs[0].sender == "autobot"
        assert beta_msgs[0].sender == "autobot"
    
    def test_get_communication_stats(self):
        self.bus.send_message(Message("autobot", "beta_worker", "test1", {}), sign=False)
        self.bus.send_message(Message("alpha_evaluator", "beta_worker", "test2", {}), sign=False)
        self.bus.send_message(Message("beta_worker", "autobot", "test3", {}), sign=False)
        
        stats = self.bus.get_communication_stats()
        
        assert stats["total_messages"] == 3
        assert stats["messages_by_type"]["test1"] == 1
        assert stats["messages_by_sender"]["autobot"] == 1
        assert stats["messages_by_receiver"]["beta_worker"] == 2


class TestAgentCommunication:
    def setup_method(self):
        self.bus = MessageBus()
        self.comm = AgentCommunication("autobot", self.bus)
        self.messages_dir = Path("messages")
        try:
            if self.messages_dir.exists():
                shutil.rmtree(self.messages_dir, ignore_errors=True)
        except Exception:
            pass
        self.messages_dir.mkdir(exist_ok=True)
    
    def teardown_method(self):
        try:
            if self.messages_dir.exists():
                shutil.rmtree(self.messages_dir, ignore_errors=True)
        except Exception:
            pass
    
    def test_send(self):
        message_id = self.comm.send("beta_worker", "request", {"task": "test"})
        
        assert message_id is not None
        assert len(self.comm.communication_history) == 1
        assert self.comm.communication_history[0]["direction"] == "sent"
    
    def test_receive(self):
        self.bus.send_message(Message("beta_worker", "autobot", "response", {}), sign=False)
        
        messages = self.comm.receive(limit=10)
        assert len(messages) == 1
        assert messages[0].sender == "beta_worker"
        assert len(self.comm.communication_history) == 1
        assert self.comm.communication_history[0]["direction"] == "received"
    
    def test_get_pending_count(self):
        self.bus.send_message(Message("beta_worker", "autobot", "msg1", {}), sign=False)
        self.bus.send_message(Message("alpha_evaluator", "autobot", "msg2", {}), sign=False)
        
        assert self.comm.get_pending_count() == 2


class TestCommunicationFunctions:
    def setup_method(self):
        self.messages_dir = Path("messages")
        try:
            if self.messages_dir.exists():
                shutil.rmtree(self.messages_dir, ignore_errors=True)
        except Exception:
            pass
        self.messages_dir.mkdir(exist_ok=True)
        
        from core.communication import _message_bus
        import core.communication
        core.communication._message_bus = None
    
    def teardown_method(self):
        try:
            if self.messages_dir.exists():
                shutil.rmtree(self.messages_dir, ignore_errors=True)
        except Exception:
            pass
    
    def test_send_message_function(self):
        message_id = send_message("autobot", "beta_worker", "test", {"data": "value"})
        assert message_id is not None
    
    def test_receive_messages_function(self):
        send_message("beta_worker", "autobot", "test", {})
        messages = receive_messages("autobot")
        assert len(messages) == 1
    
    def test_broadcast_message_function(self):
        broadcast_message("autobot", "announcement", {"info": "test"})
        
        alpha_msgs = receive_messages("alpha_evaluator")
        beta_msgs = receive_messages("beta_worker")
        
        assert len(alpha_msgs) == 1
        assert len(beta_msgs) == 1
    
    def test_get_communication_stats_function(self):
        send_message("autobot", "beta_worker", "test", {})
        stats = get_communication_stats()
        assert stats["total_messages"] == 1
