"""SAGE Dialogue Module.

This module implements the conversation engine for SAGE, including:
- Prompt building from templates
- Structured output parsing (SAGEResponse)
- Mode management and transitions
- Mid-session state change detection
- Main conversation loop

Usage:
    from sage.dialogue import ConversationEngine, create_conversation_engine

    # Create engine
    engine = create_conversation_engine(graph, api_key)

    # Start session
    session, mode = engine.start_session(learner_id)

    # Process turns
    response = engine.process_turn(user_message)

    # End session
    session = engine.end_session()
"""

from sage.dialogue.conversation import (
    ConversationConfig,
    ConversationEngine,
    create_conversation_engine,
    run_conversation,
)
from sage.dialogue.modes import (
    ModeBehavior,
    ModeManager,
    get_mode_prompt_name,
    get_transition_signals,
    should_verify_before_building,
)
from sage.dialogue.prompt_builder import (
    PromptBuilder,
    PromptTemplates,
    build_messages_for_llm,
)
from sage.dialogue.state_detection import (
    AdaptationRecommendation,
    StateChangeSignal,
    detect_explicit_signals,
    detect_implicit_signals,
    get_adaptation_for_signal,
    get_prompt_instructions_for_detection,
    update_context_for_state_change,
)
from sage.dialogue.structured_output import (
    ApplicationDetected,
    ConnectionDiscovered,
    FollowupResponse,
    GapIdentified,
    ProofEarned,
    ProofExchange,
    SAGEResponse,
    StateChange,
    create_fallback_response,
    get_output_instructions,
    get_valid_transitions,
    parse_sage_response,
    validate_response_consistency,
)


__all__ = [
    # Conversation
    "ConversationConfig",
    "ConversationEngine",
    "create_conversation_engine",
    "run_conversation",
    # Modes
    "ModeBehavior",
    "ModeManager",
    "get_mode_prompt_name",
    "get_transition_signals",
    "should_verify_before_building",
    # Prompt building
    "PromptBuilder",
    "PromptTemplates",
    "build_messages_for_llm",
    # State detection
    "AdaptationRecommendation",
    "StateChangeSignal",
    "detect_explicit_signals",
    "detect_implicit_signals",
    "get_adaptation_for_signal",
    "get_prompt_instructions_for_detection",
    "update_context_for_state_change",
    # Structured output
    "ApplicationDetected",
    "ConnectionDiscovered",
    "FollowupResponse",
    "GapIdentified",
    "ProofEarned",
    "ProofExchange",
    "SAGEResponse",
    "StateChange",
    "create_fallback_response",
    "get_output_instructions",
    "get_valid_transitions",
    "parse_sage_response",
    "validate_response_consistency",
]
