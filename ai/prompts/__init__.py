"""
Prompt templates shared across the AI chat prototype.

프롬프트 구조:
- persona.py: 슈킹 페르소나 (공통)
- system.py: 일반 대화 시스템 프롬프트
- intent.py: Intent 분류 프롬프트
- clarifying.py: 파라미터 수집 프롬프트
- synthesis.py: 계산 결과 답변 프롬프트
"""

# System prompts
from .system import DEFAULT_SYSTEM_PROMPT

# Intent classification
from .intent import CLARIFYING_INTENT_DETECTION_PROMPT, INTENT_CLASSIFICATION_PROMPT

# Clarifying prompts
from .clarifying import (
    CLARIFYING_QUESTIONS,
    PARAMETER_EXTRACTION_PROMPT,
    QUESTION_GENERATION_PROMPT,
)

# Synthesis prompts
from .synthesis import (
    FEW_SHOT_EXAMPLES,
    SYNTHESIS_PROMPT,
    get_synthesis_prompt_with_examples,
)

# Persona (공통)
from .persona import CALCULATION_DISCLAIMER, SUKING_PERSONA

__all__ = [
    # System
    "DEFAULT_SYSTEM_PROMPT",
    # Intent
    "INTENT_CLASSIFICATION_PROMPT",
    "CLARIFYING_INTENT_DETECTION_PROMPT",
    # Clarifying
    "PARAMETER_EXTRACTION_PROMPT",
    "CLARIFYING_QUESTIONS",
    "QUESTION_GENERATION_PROMPT",
    # Synthesis
    "SYNTHESIS_PROMPT",
    "FEW_SHOT_EXAMPLES",
    "get_synthesis_prompt_with_examples",
    # Persona
    "SUKING_PERSONA",
    "CALCULATION_DISCLAIMER",
]
