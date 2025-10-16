"""증여세 계산 상수 정의 (2024년 기준)."""

from typing import Dict

# 기본 공제액 (10년간 합산)
# 주의: 증여자 기준 (예: 아버지→아들 = 직계비속)
GIFT_DEDUCTION_BASE: Dict[str, int] = {
    "배우자": 600_000_000,  # 6억원
    "직계존속": 50_000_000,  # 5천만원 (자녀→부모)
    "직계비속": 50_000_000,  # 5천만원 (부모→자녀)
    "기타친족": 10_000_000,  # 1천만원
}

# 미성년자 특례 공제 (부모→미성년자녀 증여 시)
MINOR_DEDUCTION = 20_000_000  # 2천만원

# 혼인/출산 공제 한도
MARRIAGE_DEDUCTION_LIMIT = 100_000_000  # 1억원
CHILDBIRTH_DEDUCTION_LIMIT = 100_000_000  # 1억원

# 세대생략 할증률
GENERATION_SKIPPING_SURTAX_RATE = 0.30  # 30%

# 세율 구조 (과세표준 기준)
TAX_BRACKETS = [
    {"limit": 100_000_000, "rate": 0.10, "progressive_deduction": 0},
    {"limit": 500_000_000, "rate": 0.20, "progressive_deduction": 10_000_000},
    {"limit": 1_000_000_000, "rate": 0.30, "progressive_deduction": 60_000_000},
    {"limit": 3_000_000_000, "rate": 0.40, "progressive_deduction": 160_000_000},
    {"limit": float("inf"), "rate": 0.50, "progressive_deduction": 460_000_000},
]
