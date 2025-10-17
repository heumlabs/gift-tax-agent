# AI Scripts

법령 검색 시스템 관련 스크립트 모음입니다.

---

## 📁 스크립트 목록

### 1. `test.py` - 법령 검색 테스트 CLI ⭐

모든 법령 검색 테스트 기능을 통합한 CLI 도구입니다.

#### 사용법

```bash
# 대화형 검색
python ai/scripts/test.py interactive

# 검색 비교 (다른 설정과 비교)
python ai/scripts/test.py compare "증여재산 공제"

# 벤치마크 (표준 테스트셋)
python ai/scripts/test.py benchmark

# 상세 분석
python ai/scripts/test.py test "배우자 증여 공제" --top-k 10
```

#### 명령어

| 명령어 | 설명 | 옵션 |
|--------|------|------|
| `interactive` | 대화형 검색 모드 | `--v2`, `--top-k N`, `--optimize` |
| `compare <query>` | V2/V3 비교 검색 | `--top-k N` |
| `benchmark` | 벤치마크 테스트 (10개 쿼리) | - |
| `test <query>` | 단일 쿼리 상세 분석 | `--v2`, `--top-k N`, `--optimize` |

#### 예시

```bash
# 대화형으로 여러 쿼리 테스트
python ai/scripts/test.py interactive

# V2와 V3 성능 비교
python ai/scripts/test.py compare "직계존속 증여 공제"

# 벤치마크 실행
python ai/scripts/test.py benchmark

# 쿼리 최적화 사용
python ai/scripts/test.py test "부모님한테 돈 받으면" --optimize
```

---

### 2. `db_build.py` - 벡터 DB 구축

법령 JSON 데이터를 파싱하여 PostgreSQL + pgvector에 저장합니다.

```bash
python ai/scripts/db_build.py
```

**기능:**
- `.dataset/ko-law-parser/law/*.json` 파일 로드
- 조문 단위 파싱 및 임베딩 생성
- `law_sources` 테이블에 저장 (약 2,816개 레코드)

---

### 3. `db_reembed.py` - 임베딩 재생성

특정 테이블의 임베딩을 다른 모델로 재생성합니다.

```bash
python ai/scripts/db_reembed.py
```

**사용 사례:**
- 임베딩 모델 변경 시 (text-embedding-004 → gemini-embedding-001)
- 임베딩 차원 변경 시 (768D, 1536D 등)
- 정규화 적용/제거

---

### 4. `send_message.py` - 메시지 전송 테스트

챗봇 API 테스트용 메시지 전송 스크립트입니다.

```bash
python ai/scripts/send_message.py
```

---

## ⚙️ 설정

### 환경변수

검색 시스템 설정은 환경변수로 변경 가능합니다 (`backend/.env`):

```bash
# 임베딩 모델
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_EMBEDDING_DIMENSION=768

# 검색 테이블 (기본: law_sources_v3)
LAW_SEARCH_TABLE=law_sources_v3

# 하이브리드 검색 가중치
LAW_SEARCH_KEYWORD_WEIGHT=0.3   # 키워드 매칭 30%
LAW_SEARCH_EMBEDDING_WEIGHT=0.7 # 임베딩 유사도 70%
```

### 코드에서 설정

`ai/config.py`에서 기본값 확인/수정 가능:

```python
@dataclass(frozen=True)
class GeminiSettings:
    # ...
    law_search_table: str = "law_sources_v3"
    law_search_keyword_weight: float = 0.3
    law_search_embedding_weight: float = 0.7
```

---

## 📊 현재 시스템 구성

### 임베딩 모델
- **모델**: `gemini-embedding-001` (Google)
- **차원**: 768D
- **정규화**: O (cosine similarity 최적화)

### 검색 방식
- **하이브리드 검색**: 키워드 30% + 임베딩 70%
- **테이블**: `law_sources_v3`
- **총 레코드**: 2,816개 (상속세및증여세법 관련 조문)

### 성능 (벤치마크 기준)
- **발견율**: 90% (10개 쿼리 중 9개 발견)
- **Top-3 정확도**: 70%
- **V2 대비 개선**: +30%p (40% → 70%)

---

## 🔍 검색 품질 개선 히스토리

### V1 (초기)
- 모델: text-embedding-004
- 정규화: X
- 성능: 낮음

### V2
- 모델: text-embedding-004
- 하이브리드 검색 도입 (키워드 + 임베딩)
- 성능: 중간

### V3 (현재) ✅
- 모델: gemini-embedding-001
- 차원: 768D + 정규화
- 하이브리드 검색 유지
- **성능: Top-3 정확도 70%**
