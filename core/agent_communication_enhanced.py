"""Inter-agent discussion space for council deliberation on mutations."""

from __future__ import annotations

import json
import uuid
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.communication import (
    get_message_bus,
    send_message,
    receive_messages,
    Message,
)


class CouncilDiscussionSpace:
    """Shared space where agents reason together about mutations."""

    def __init__(self):
        self._discussions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def open_discussion(self, topic: str, mutation_id: Optional[str] = None) -> Dict[str, Any]:
        """Open a new discussion thread."""
        discussion_id = f"disc_{uuid.uuid4().hex[:12]}"
        with self._lock:
            self._discussions[discussion_id] = {
                "id": discussion_id,
                "topic": topic,
                "mutation_id": mutation_id,
                "participants": {},
                "messages": [],
                "consensus": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return self._discussions[discussion_id]

    def agent_contributes(
        self,
        discussion_id: str,
        agent_name: str,
        thoughts: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Record an agent's contribution and detect consensus."""
        with self._lock:
            discussion = self._discussions.get(discussion_id)
            if not discussion:
                return None

            contribution = {
                "agent_name": agent_name,
                "thoughts": thoughts,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            discussion["participants"][agent_name] = thoughts
            discussion["messages"].append(contribution)

        consensus = self._detect_consensus(discussion_id)
        with self._lock:
            discussion = self._discussions.get(discussion_id)
            if discussion:
                discussion["consensus"] = consensus
        return consensus

    def get_discussion_summary(self, discussion_id: str) -> Optional[Dict[str, Any]]:
        """Get shared reasoning state from the discussion."""
        with self._lock:
            discussion = self._discussions.get(discussion_id)
            if not discussion:
                return None
            return {
                "id": discussion["id"],
                "topic": discussion["topic"],
                "mutation_id": discussion.get("mutation_id"),
                "participants": dict(discussion["participants"]),
                "consensus": discussion.get("consensus"),
                "timestamp": discussion["timestamp"],
            }

    def _detect_consensus(self, discussion_id: str) -> Optional[Dict[str, Any]]:
        """Detect consensus from contributions."""
        with self._lock:
            discussion = self._discussions.get(discussion_id)
            if not discussion:
                return None

        votes = {}
        for agent_name, thoughts in discussion["participants"].items():
            vote = thoughts.get("vote")
            reasoning = thoughts.get("reasoning", "")
            votes[agent_name] = {"vote": vote, "reasoning": reasoning}

        approve_count = sum(1 for v in votes.values() if v.get("vote") == "approve")
        reject_count = sum(1 for v in votes.values() if v.get("vote") == "reject")
        total = len(votes)

        if total == 0:
            return None

        if approve_count == total:
            return {"status": "unanimous_approve", "votes": votes}
        if reject_count == total:
            return {"status": "unanimous_reject", "votes": votes}
        if approve_count > reject_count:
            return {"status": "majority_approve", "votes": votes}
        if reject_count > approve_count:
            return {"status": "majority_reject", "votes": votes}
        return {"status": "split", "votes": votes}

    def list_discussions(self) -> List[Dict[str, Any]]:
        """List all discussions."""
        with self._lock:
            return [
                {
                    "id": d["id"],
                    "topic": d["topic"],
                    "mutation_id": d.get("mutation_id"),
                    "participants": list(d["participants"].keys()),
                    "consensus": d.get("consensus"),
                    "timestamp": d["timestamp"],
                }
                for d in self._discussions.values()
            ]


_discussion_space = None


def get_discussion_space() -> CouncilDiscussionSpace:
    global _discussion_space
    if _discussion_space is None:
        _discussion_space = CouncilDiscussionSpace()
    return _discussion_space
