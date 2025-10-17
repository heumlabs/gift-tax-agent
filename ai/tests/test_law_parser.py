"""Tests for law JSON parsing logic."""

from __future__ import annotations

import sys
from pathlib import Path

# ai.scripts 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.build_law_vector_db import (
    build_full_reference,
    chunk_text,
    compute_chunk_hash,
    parse_law_json,
)


class TestLawParser:
    """법령 JSON 파싱 로직 테스트"""

    def test_build_full_reference_simple(self):
        """단순 참조 경로 생성 테스트"""
        law_name = "상속세및증여세법"
        path = ["제1장 총칙", "제1조(목적)"]

        result = build_full_reference(law_name, path)

        assert result == "상속세및증여세법 제1장 총칙 제1조(목적)"

    def test_build_full_reference_with_content(self):
        """본문 텍스트가 포함된 경로 테스트"""
        law_name = "상속세및증여세법"
        path = ["제1장 총칙", "제1조(목적)", "이 법은 상속세 및 증여세의..."]

        result = build_full_reference(law_name, path)

        # 본문 텍스트(50자 이상)는 필터링되어야 함
        assert "이 법은" not in result
        assert "제1장" in result
        assert "제1조" in result

    def test_build_full_reference_nested(self):
        """중첩된 구조 테스트"""
        law_name = "국세기본법"
        path = ["제1편 총칙", "제1장", "제1조", "1항", "가목"]

        result = build_full_reference(law_name, path)

        assert "국세기본법" in result
        assert "제1편" in result
        assert "제1장" in result
        assert "제1조" in result

    def test_chunk_text_short(self):
        """짧은 텍스트 분할 테스트"""
        text = "짧은 텍스트입니다."

        chunks = chunk_text(text, max_chars=500)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_long(self):
        """긴 텍스트 분할 테스트"""
        # 600자 텍스트 생성
        text = "이것은 테스트 문장입니다. " * 30  # ~600자

        chunks = chunk_text(text, max_chars=500)

        assert len(chunks) >= 2
        assert all(len(chunk) <= 500 for chunk in chunks)
        # 모든 청크 합치면 원본과 유사해야 함 (공백 차이 가능)
        assert "테스트 문장" in "".join(chunks)

    def test_chunk_text_sentence_boundary(self):
        """문장 경계 고려 테스트"""
        text = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."

        chunks = chunk_text(text, max_chars=30)

        # 문장 경계에서 분할되어야 함
        assert len(chunks) >= 2
        for chunk in chunks:
            if chunk.strip():
                assert chunk.strip().endswith("다.") or chunks[-1] == chunk

    def test_compute_chunk_hash(self):
        """청크 해시 생성 테스트"""
        law_name = "상속세및증여세법"
        full_ref = "상속세및증여세법 제53조"
        content = "증여재산공제는 다음과 같다."

        hash1 = compute_chunk_hash(law_name, full_ref, content)
        hash2 = compute_chunk_hash(law_name, full_ref, content)

        # 동일 입력 → 동일 해시
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 = 64 hex chars

    def test_compute_chunk_hash_different_content(self):
        """다른 내용의 해시는 달라야 함"""
        law_name = "상속세및증여세법"
        full_ref = "상속세및증여세법 제53조"

        hash1 = compute_chunk_hash(law_name, full_ref, "내용1")
        hash2 = compute_chunk_hash(law_name, full_ref, "내용2")

        assert hash1 != hash2

    def test_parse_law_json_simple(self):
        """간단한 JSON 파싱 테스트"""
        law_name = "테스트법"
        data = {
            "제1장 총칙": {
                "제1조(목적)": {
                    "이 법은 테스트를 목적으로 한다.": {}
                }
            }
        }
        source_file = "test.json"

        chunks = list(parse_law_json(law_name, data, source_file))

        assert len(chunks) > 0
        assert chunks[0].law_name == law_name
        assert "제1장" in chunks[0].full_reference
        assert "테스트를 목적" in chunks[0].content

    def test_parse_law_json_nested(self):
        """중첩 구조 JSON 파싱 테스트"""
        law_name = "테스트법"
        data = {
            "제1장": {
                "제1조": {
                    "본문입니다.": {
                        "1항": {
                            "첫 번째 항목입니다.": {}
                        },
                        "2항": {
                            "두 번째 항목입니다.": {}
                        }
                    }
                }
            }
        }
        source_file = "test.json"

        chunks = list(parse_law_json(law_name, data, source_file))

        # 3개의 텍스트 노드 (본문, 1항, 2항)
        assert len(chunks) == 3
        contents = [c.content for c in chunks]
        assert any("본문입니다" in c for c in contents)
        assert any("첫 번째 항목" in c for c in contents)
        assert any("두 번째 항목" in c for c in contents)

    def test_parse_law_json_skip_short(self):
        """10자 미만 텍스트는 스킵해야 함"""
        law_name = "테스트법"
        data = {
            "제1조": {
                "짧음": {},  # 3자 → 스킵
                "충분히 긴 텍스트입니다.": {}  # 정상 처리
            }
        }
        source_file = "test.json"

        chunks = list(parse_law_json(law_name, data, source_file))

        # "짧음"은 스킵되어야 함
        assert len(chunks) == 1
        assert "충분히 긴" in chunks[0].content
        assert "짧음" not in chunks[0].content
