from typing import Dict, Any, List
import hashlib
import json
from governance.audit_log import log_consensus_vote, log_code_mutation

class ConsensusEngine:
    def __init__(self, agents: List[str]):
        self.agents = agents
        self.proposals: Dict[str, Dict] = {}
        self.votes: Dict[str, Dict[str, str]] = {}
        self.stable_hash: str = ""
    
    def create_proposal(self, proposal_id: str, agent_name: str, description: str, changes: Dict[str, Any]) -> str:
        self.proposals[proposal_id] = {
            "agent": agent_name,
            "description": description,
            "changes": changes,
            "status": "pending"
        }
        self.votes[proposal_id] = {}
        return proposal_id
    
    def cast_vote(self, proposal_id: str, agent_name: str, vote: str, reason: str) -> bool:
        if proposal_id not in self.proposals:
            return False
        
        if agent_name not in self.agents:
            return False
        
        if vote not in ["approve", "reject"]:
            return False
        
        self.votes[proposal_id][agent_name] = vote
        log_consensus_vote(agent_name, proposal_id, vote, reason)
        
        return True
    
    def check_consensus(self, proposal_id: str) -> str:
        if proposal_id not in self.votes:
            return "pending"
        
        votes = self.votes[proposal_id]
        
        if len(votes) < len(self.agents):
            return "pending"
        
        if all(v == "approve" for v in votes.values()):
            self.proposals[proposal_id]["status"] = "approved"
            return "approved"
        else:
            self.proposals[proposal_id]["status"] = "rejected"
            return "rejected"
    
    def get_stable_hash(self) -> str:
        return self.stable_hash
    
    def update_stable_hash(self, codebase_state: Dict[str, Any]) -> str:
        state_json = json.dumps(codebase_state, sort_keys=True)
        self.stable_hash = hashlib.sha256(state_json.encode()).hexdigest()
        return self.stable_hash

class StaggeredRollout:
    def __init__(self, consensus_engine: ConsensusEngine):
        self.consensus = consensus_engine
        self.mutating_node: str = None
        self.stable_nodes: List[str] = []
    
    def start_mutation(self, node_name: str, all_nodes: List[str]):
        self.mutating_node = node_name
        self.stable_nodes = [n for n in all_nodes if n != node_name]
        print(f"[ROLLOUT] Node {node_name} mutating, nodes {self.stable_nodes} monitoring")
    
    def validate_mutation(self, node_name: str, changes: Dict[str, Any]) -> bool:
        if node_name != self.mutating_node:
            print(f"[ROLLOUT] Unauthorized mutation attempt by {node_name}")
            return False
        
        proposal_id = f"mutation_{node_name}_{hashlib.sha256(json.dumps(changes, sort_keys=True).encode()).hexdigest()[:8]}"
        self.consensus.create_proposal(proposal_id, node_name, f"Code mutation by {node_name}", changes)
        
        for monitor in self.stable_nodes:
            self.consensus.cast_vote(proposal_id, monitor, "approve", f"Monitoring node {monitor} approves")
        
        result = self.consensus.check_consensus(proposal_id)
        
        if result == "approved":
            print(f"[ROLLOUT] Mutation by {node_name} approved")
            return True
        else:
            print(f"[ROLLOUT] Mutation by {node_name} rejected, rolling back")
            return False
    
    def complete_mutation(self, node_name: str, new_hash: str):
        self.mutating_node = None
        self.stable_nodes = []
        print(f"[ROLLOUT] Mutation complete, new stable hash: {new_hash}")
