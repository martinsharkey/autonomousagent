"""Telegram /mutate command - operator injects mutations at highest priority.

Usage via Telegram: /mutate <description of what to build>

Operator mutations:
- Auto-approved (operator trust level)
- Priority 100 (highest)
- Bypass council voting
- Get implemented immediately if they have file_changes
"""

from __future__ import annotations

from typing import Optional


async def handle_mutate_command(text: str, operator_name: str = "human_operator") -> str:
    """
    Process a /mutate command from the operator.
    
    Args:
        text: The mutation description (everything after /mutate)
        operator_name: Who is requesting this
        
    Returns:
        Status message to send back via Telegram
    """
    if not text or not text.strip():
        return (
            "Usage: /mutate <description>\n"
            "Example: /mutate Add a web scraper tool for research\n"
            "Example: /mutate Improve error handling in agent_loop\n\n"
            "Your request will be auto-approved and queued for implementation."
        )

    description = text.strip()

    try:
        from core.evolution import get_evolution_engine, MutationType

        engine = get_evolution_engine()

        # Create mutation as operator request
        mutation = engine.propose_mutation(
            agent_name=operator_name,
            mutation_type=MutationType.BEHAVIOR_CHANGE,
            description=description,
            rationale=f"Operator priority request: {description}",
            proposed_changes={"operator_request": description, "priority": 100},
            expected_improvement=0.5,
            risk_level="low",
        )

        # Check if it was rejected by safety gates
        if mutation.status.value == "rejected":
            return f"❌ Rejected: {mutation.rejection_reason}\n\nTry rephrasing or be more specific."

        # Auto-approve operator mutations
        engine.approve_mutation(mutation.mutation_id, approved_by=operator_name)

        # Sync to roadmap (centrally tracked)
        try:
            from core.roadmap_sync import sync_to_roadmap
            sync_to_roadmap(mutation.to_dict())
        except Exception:
            pass

        return (
            f"✅ Mutation approved: `{mutation.mutation_id[:12]}`\n"
            f"📋 {description}\n"
            f"🎯 Pillar: {mutation.mission_pillar or 'auto'}\n"
            f"⚡ Priority: OPERATOR (highest)\n\n"
            f"The council will implement this on the next evolution cycle."
        )

    except Exception as e:
        return f"❌ Error creating mutation: {str(e)[:200]}"
