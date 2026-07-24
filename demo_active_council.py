#!/usr/bin/env python3
"""
Active Council Demo - Demonstrates inter-agent communication, learning, and collaboration
This demo shows the council members actively communicating, learning from trajectories,
and improving their performance over time.
"""

import json
import time
from datetime import datetime
from typing import Dict, Any

from core.communication import (
    get_message_bus,
    get_agent_communication,
    send_message,
    receive_messages,
    broadcast_message,
    get_communication_stats
)
from core.data_logger import log_trajectory, get_trajectories
from core.learning import learn_from_session, get_learning_summary
from core.state import AgentState
from governance.audit_log import log_event

class ActiveCouncilDemo:
    def __init__(self, session_id: str = None):
        self.session_id = session_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.agents = ["autobot", "alpha_evaluator", "beta_worker"]
        self.message_bus = get_message_bus()
        
        print("\n" + "="*70)
        print("ACTIVE COUNCIL DEMO - Inter-Agent Communication & Learning")
        print("="*70)
        print(f"Session ID: {self.session_id}")
        print(f"Agents: {', '.join(self.agents)}")
        print("="*70 + "\n")
    
    def demonstrate_communication(self):
        print("\n[PHASE 1] Demonstrating Inter-Agent Communication")
        print("-" * 70)
        
        autobot_comm = get_agent_communication("autobot")
        alpha_comm = get_agent_communication("alpha_evaluator")
        beta_comm = get_agent_communication("beta_worker")
        
        print("\n1. Autobot broadcasts task initialization to all agents...")
        broadcast_message(
            sender="autobot",
            message_type="task_init",
            content={
                "task": "Implement a web scraper for product data",
                "requirements": ["Extract product names", "Get prices", "Save to JSON"],
                "priority": "high"
            },
            metadata={"session": self.session_id}
        )
        time.sleep(0.5)
        
        print("2. Beta Worker responds with implementation plan...")
        beta_comm.send(
            receiver="autobot",
            message_type="implementation_plan",
            content={
                "approach": "Use requests + BeautifulSoup",
                "estimated_time": "30 minutes",
                "confidence": 0.85
            }
        )
        time.sleep(0.5)
        
        print("3. Alpha Evaluator reviews the plan and provides feedback...")
        alpha_comm.send(
            receiver="beta_worker",
            message_type="review_feedback",
            content={
                "approval": "conditional",
                "suggestions": [
                    "Add error handling for network timeouts",
                    "Include rate limiting to avoid being blocked",
                    "Validate extracted data before saving"
                ],
                "quality_score": 0.75
            }
        )
        time.sleep(0.5)
        
        print("4. Beta Worker acknowledges and incorporates feedback...")
        beta_comm.send(
            receiver="alpha_evaluator",
            message_type="acknowledgment",
            content={
                "accepted_suggestions": 3,
                "revised_confidence": 0.92,
                "status": "implementing"
            }
        )
        time.sleep(0.5)
        
        print("5. Autobot coordinates final consensus...")
        autobot_comm.send(
            receiver="beta_worker",
            message_type="approval",
            content={
                "status": "approved",
                "proceed": True,
                "monitoring": "active"
            }
        )
        
        time.sleep(1)
        
        print("\nCommunication Statistics:")
        stats = get_communication_stats()
        print(f"  Total messages: {stats['total_messages']}")
        print(f"  Messages by type: {dict(stats['messages_by_type'])}")
        print(f"  Messages by sender: {dict(stats['messages_by_sender'])}")
        print(f"  Pending messages: {stats['pending_messages']}")
    
    def demonstrate_trajectory_capture(self):
        print("\n\n[PHASE 2] Capturing Agent Trajectories")
        print("-" * 70)
        
        print("\n1. Logging Autobot coordination trajectory...")
        log_trajectory(
            agent_name="autobot",
            state={"phase": "coordination", "loop_count": 1},
            prompt="Coordinate web scraper implementation",
            response="Assigned task to beta_worker with requirements",
            reward=0.9,
            session_id=self.session_id,
            metadata={"role": "coordinator"}
        )
        
        print("2. Logging Beta Worker implementation trajectory...")
        log_trajectory(
            agent_name="beta_worker",
            state={"phase": "implementation", "loop_count": 1},
            prompt="Implement web scraper with error handling",
            response="Created scraper with requests + BeautifulSoup, added retry logic",
            reward=0.85,
            session_id=self.session_id,
            metadata={"role": "implementer"}
        )
        
        print("3. Logging Alpha Evaluator review trajectory...")
        log_trajectory(
            agent_name="alpha_evaluator",
            state={"phase": "review", "loop_count": 1},
            prompt="Review beta_worker's implementation",
            response="Approved with suggestions for error handling and rate limiting",
            reward=0.88,
            session_id=self.session_id,
            metadata={"role": "reviewer"}
        )
        
        print("4. Logging additional trajectories for learning...")
        for i in range(2, 5):
            log_trajectory(
                agent_name="autobot",
                state={"phase": "coordination", "loop_count": i},
                prompt=f"Coordinate task iteration {i}",
                response=f"Successfully coordinated iteration {i}",
                reward=0.85 + (i * 0.02),
                session_id=self.session_id
            )
            
            log_trajectory(
                agent_name="beta_worker",
                state={"phase": "implementation", "loop_count": i},
                prompt=f"Implement feature iteration {i}",
                response=f"Completed implementation with improvements",
                reward=0.80 + (i * 0.03),
                session_id=self.session_id
            )
        
        trajectories = get_trajectories(session_id=self.session_id)
        print(f"\nTotal trajectories captured: {len(trajectories)}")
        for agent in self.agents:
            agent_trajs = [t for t in trajectories if t["agent"] == agent]
            avg_reward = sum(t["reward"] for t in agent_trajs) / len(agent_trajs) if agent_trajs else 0
            print(f"  {agent}: {len(agent_trajs)} trajectories, avg reward: {avg_reward:.2f}")
    
    def demonstrate_learning(self):
        print("\n\n[PHASE 3] Learning from Trajectories")
        print("-" * 70)
        
        print("\n1. Analyzing trajectories and extracting patterns...")
        learning_results = learn_from_session(self.session_id, self.agents)
        
        print("\n2. Learning Results by Agent:")
        for agent_name, analysis in learning_results.items():
            print(f"\n  [{agent_name.upper()}]")
            print(f"    Total trajectories: {analysis['total_trajectories']}")
            print(f"    Successful: {len(analysis['successful'])}")
            print(f"    Failed: {len(analysis['failed'])}")
            print(f"    Patterns detected: {len(analysis['patterns'])}")
            
            if analysis['recommendations']:
                print(f"    Recommendations:")
                for rec in analysis['recommendations'][:3]:
                    print(f"      - {rec}")
        
        print("\n3. Checking for learning feedback messages...")
        time.sleep(1)
        
        for agent_name in self.agents:
            comm = get_agent_communication(agent_name)
            messages = comm.receive(limit=10)
            
            feedback_messages = [m for m in messages if m.message_type == "feedback"]
            if feedback_messages:
                print(f"\n  {agent_name} received {len(feedback_messages)} feedback message(s):")
                for msg in feedback_messages:
                    content = msg.content
                    print(f"    - Recommendations: {len(content.get('recommendations', []))}")
                    print(f"    - Patterns: {content.get('patterns_count', 0)}")
                    print(f"    - Success rate: {content.get('successful_count', 0)}/{content.get('successful_count', 0) + content.get('failed_count', 0)}")
    
    def demonstrate_learning_summary(self):
        print("\n\n[PHASE 4] Learning Summary & Insights")
        print("-" * 70)
        
        summary = get_learning_summary()
        
        print(f"\nOverall Learning Statistics:")
        print(f"  Total sessions learned: {summary['total_sessions']}")
        print(f"  Total patterns extracted: {summary['total_patterns']}")
        print(f"  Total recommendations generated: {summary['total_recommendations']}")
        
        print(f"\nAgents Learning Progress:")
        for agent_name, count in summary['agents_learned'].items():
            print(f"  {agent_name}: {count} learning sessions")
    
    def demonstrate_full_workflow(self):
        print("\n\n[PHASE 5] Full Workflow Demonstration")
        print("-" * 70)
        
        print("\n1. Council receives new task...")
        log_event("task_received", "system", "new_task", {"task": "Build API integration"})
        time.sleep(0.5)
        
        print("2. Autobot analyzes task and delegates...")
        autobot_comm = get_agent_communication("autobot")
        autobot_comm.send(
            receiver="beta_worker",
            message_type="task_delegation",
            content={
                "task": "Build REST API integration",
                "endpoints": ["GET /data", "POST /submit"],
                "auth": "Bearer token"
            }
        )
        time.sleep(0.5)
        
        print("3. Beta Worker implements solution...")
        beta_comm = get_agent_communication("beta_worker")
        beta_comm.send(
            receiver="alpha_evaluator",
            message_type="implementation_complete",
            content={
                "files_created": ["api_client.py", "endpoints.py"],
                "tests_passing": True,
                "coverage": 0.87
            }
        )
        time.sleep(0.5)
        
        print("4. Alpha Evaluator reviews and approves...")
        alpha_comm = get_agent_communication("alpha_evaluator")
        alpha_comm.send(
            receiver="autobot",
            message_type="review_complete",
            content={
                "approved": True,
                "quality_score": 0.91,
                "suggestions": ["Add logging", "Improve error messages"]
            }
        )
        time.sleep(0.5)
        
        print("5. Autobot logs successful trajectory...")
        log_trajectory(
            agent_name="autobot",
            state={"phase": "coordination", "loop_count": 1},
            prompt="Coordinate API integration task",
            response="Successfully delegated and coordinated implementation",
            reward=0.95,
            session_id=self.session_id,
            metadata={"outcome": "success"}
        )
        
        log_trajectory(
            agent_name="beta_worker",
            state={"phase": "implementation", "loop_count": 1},
            prompt="Implement REST API integration",
            response="Created API client with full test coverage",
            reward=0.92,
            session_id=self.session_id,
            metadata={"outcome": "success"}
        )
        
        log_trajectory(
            agent_name="alpha_evaluator",
            state={"phase": "review", "loop_count": 1},
            prompt="Review API implementation",
            response="Approved with high quality score",
            reward=0.93,
            session_id=self.session_id,
            metadata={"outcome": "success"}
        )
        
        print("\n6. Learning engine analyzes new trajectories...")
        learn_from_session(self.session_id, self.agents)
        
        print("\n7. Final communication statistics:")
        stats = get_communication_stats()
        print(f"   Total messages exchanged: {stats['total_messages']}")
        print(f"   Message types: {dict(stats['messages_by_type'])}")
    
    def run_full_demo(self):
        print("\n" + "="*70)
        print("RUNNING FULL ACTIVE COUNCIL DEMO")
        print("="*70)
        
        self.demonstrate_communication()
        self.demonstrate_trajectory_capture()
        self.demonstrate_learning()
        self.demonstrate_learning_summary()
        self.demonstrate_full_workflow()
        
        print("\n\n" + "="*70)
        print("DEMO COMPLETE")
        print("="*70)
        print("\nKey Achievements:")
        print("  ✓ Inter-agent communication established")
        print("  ✓ Trajectories captured for all agents")
        print("  ✓ Learning patterns extracted")
        print("  ✓ Feedback provided to agents")
        print("  ✓ Full workflow demonstrated")
        print("\nEvidence Files:")
        print(f"  - Messages: messages/")
        print(f"  - Trajectories: trajectories/{self.session_id}/")
        print(f"  - Learning: learning/")
        print(f"  - Audit logs: audit_logs/")
        print("="*70 + "\n")


def main():
    demo = ActiveCouncilDemo()
    demo.run_full_demo()


if __name__ == "__main__":
    main()
