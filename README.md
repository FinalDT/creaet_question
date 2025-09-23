# 📚 한국 중학교 수학 문제 생성기

AI를 활용해 한국 중학교 수학 문제를 자동으로 생성하는 Azure Functions 서비스입니다.

## 🎯 프로젝트 목적

- **AI 문제 생성**: GPT-4를 사용해 중학교 수준의 수학 문제 자동 생성
- **개인화 문제**: 학습자별 맞춤형 문제 생성 (뷰 기반)
- **시각 자료 제공**: 기하, 그래프 문제에 SVG 이미지 자동 생성 (문제-그림 완벽 일치)
- **데이터베이스 연동**: SQL Server에서 기존 문제 정보를 가져와 학습에 활용
- **REST API 제공**: 웹/앱에서 쉽게 사용할 수 있는 API 서비스

## 🚀 주요 기능

### 1. 일반 문제 생성 (`/api/create_question`)
- 주제별 맞춤 문제 생성
- 선택형/서술형 문제 지원
- 자동 SVG 이미지 생성 (기하, 그래프 문제)
- LaTeX 수식 지원

### 2. 대량 생성 (`/api/bulk_generate`)
- 여러 문제를 한 번에 생성 (20개)
- 배치 처리로 효율적인 생성
- 터미널 실시간 진행 상황 표시

### 3. 🎯 개인화 문제 생성 (`/api/create_by_view`) ⭐ **신규**
- `vw_personal_item_enriched` 뷰 기반 개인화 문제 생성
- 학습자별 맞춤형 문제 (assessmentItemID, knowledgeTag 기반)
- 같은 주제 내 중복 방지 로직
- 난이도별 문제 길이 조절 (쉬움: 1-2문장, 중간: 3문장, 어려움: 4문장)

### 4. 연결 테스트 (`/api/test_connections`)
- Azure OpenAI 연결 상태 확인
- SQL Server 연결 상태 확인

## 🛠️ 사용 기술

- **Azure Functions** - 서버리스 API 서비스
- **Azure OpenAI (GPT-4)** - AI 문제 생성
- **SQL Server** - 문제 데이터베이스
- **Python** - 백엔드 개발
- **SVG** - 수학 도형/그래프 시각화

## 📋 필요 조건

- Python 3.8+
- Azure Functions Core Tools
- Azure OpenAI 서비스
- SQL Server 데이터베이스

## ⚡ 빠른 시작

### 1. 프로젝트 복사
```bash
git clone https://github.com/FinalDT/creaet_question.git
cd creaet_question
```

### 2. 가상환경 설정
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 환경 설정
`local.settings.json` 파일에 다음 정보 입력:
```json
{
  "Values": {
    "AOAI_ENDPOINT": "Azure OpenAI 엔드포인트",
    "AOAI_KEY": "Azure OpenAI 키",
    "AOAI_DEPLOYMENT": "gpt-4o-create_question",
    "SQL_CONNECTION": "SQL Server 연결 문자열"
  }
}
```

### 4. 서비스 실행
```bash
# 방법 1: 배치 파일 사용
start.bat

# 방법 2: 직접 실행
func start
```

## 📖 API 사용법

### 🎯 개인화 문제 생성 (신규)
```http
GET http://localhost:7071/api/create_by_view
또는
POST http://localhost:7071/api/create_by_view
{
  "learner_id": "L001"
}
```

### 📚 대량 문제 생성
```http
GET http://localhost:7071/api/bulk_generate
```

### 📝 일반 문제 생성
```http
POST http://localhost:7071/api/create_question
Content-Type: application/json

{
  "topic_name": "이차함수"
}
```

### 🔍 연결 테스트
```http
GET http://localhost:7071/api/test_connections
```

## 📋 응답 예시

### create_by_view 응답
```json
{
  "success": true,
  "generated_questions": [
    {
      "assessmentItemID": "A070123001",
      "question_text": "아래 그림에서 삼각형 △ABC의 세 각 ∠A, ∠B, ∠C의 합은 얼마인가?",
      "question_type": "선택형",
      "choices": ["① 90°", "② 120°", "③ 180°", "④ 240°", "⑤ 360°"],
      "correct_answer": "③",
      "answer_explanation": "삼각형의 세 내각의 합은 항상 180°입니다.",
      "svg_content": "<svg viewBox='0 0 400 300' width='100%' height='auto'>...</svg>",
      "metadata": {
        "assessment_item_id": "A070123001",
        "knowledge_tag": 9050,
        "grade": 7,
        "term": "2학기",
        "concept_name": "삼각형의 세 내각의 크기의 합",
        "difficulty_band": "쉬움",
        "source": "vw_personal_item_enriched"
      }
    }
  ],
  "summary": {
    "total_generated": 5,
    "target_count": 5,
    "success_rate": 100.0
  }
}
```

## 🎨 SVG 이미지 기능

다음 유형의 문제에서 자동으로 시각 자료가 생성됩니다:
- 📐 기하 문제 (삼각형, 사각형, 원 등)
- 📊 함수 그래프 (일차함수, 이차함수)
- 📈 통계 차트 (막대그래프, 원그래프)
- 📏 좌표 평면 문제

## 📁 프로젝트 구조 (모듈화됨)

```
문제생성API2/
├── 📄 function_app.py              # 🚪 메인 Azure Functions 진입점
├── 📄 generate_concept_mapping.py   # 🔗 매핑 스크립트 (questions_dim ↔ gold)
├── 📄 host.json                    # ⚙️ Azure Functions 설정
├── 📄 local.settings.json          # 🔑 환경 변수 (DB, OpenAI 연결 정보)
├── 📄 requirements.txt             # 📦 Python 패키지 목록
├── 📄 start.bat                    # ▶️ 실행 스크립트
│
├── 📁 modules/                     # 🧩 핵심 모듈들
│   ├── 📁 handlers/                # 🎮 API 요청 핸들러들
│   │   └── 📄 create_by_view_handler.py  # 개인화 문제 생성 핸들러
│   │
│   ├── 📁 services/                # 🔧 비즈니스 로직 서비스들
│   │   ├── 📄 view_service.py      # 뷰 기반 개인화 문제 생성
│   │   ├── 📄 bulk_service.py      # 대량 문제 생성
│   │   ├── 📄 question_service.py  # 일반 문제 생성
│   │   └── 📄 connection_service.py # 연결 테스트
│   │
│   └── 📁 core/                    # ⚡ 공통 핵심 모듈들
│       ├── 📄 database.py          # 데이터베이스 연결/쿼리
│       ├── 📄 ai_service.py        # AI 문제 생성 (OpenAI)
│       ├── 📄 validation.py        # 문제 검증/DB 저장 준비
│       ├── 📄 utils.py             # 유틸리티 함수들
│       ├── 📄 responses.py         # API 응답 포맷
│       └── 📄 debug.py             # 디버깅 도구
│
├── 📁 mapping/                     # 🗺️ 데이터 매핑 관련
│   ├── 📄 ai_mapper.py             # AI 기반 concept 매핑
│   ├── 📄 data_loader.py           # 데이터 로딩
│   └── 📄 database_updater.py      # DB 업데이트
│
├── 📁 scripts/                     # 📜 유틸리티 스크립트들
└── 📁 .venv/                       # 🐍 Python 가상환경
```

## 🔄 API 흐름도

### 1️⃣ `/api/create_by_view` (개인화 문제 생성)
```
🌐 HTTP Request
    ↓
📄 function_app.py (라우팅)
    ↓
🎮 handlers/create_by_view_handler.py
    ↓
🔧 services/view_service.py
    ├── 📊 DB에서 vw_personal_item_enriched 조회
    ├── 🤖 AI 문제 생성 (core/ai_service.py)
    ├── ✅ 문제 검증 (core/validation.py)
    └── 📤 JSON 응답 반환
```

### 2️⃣ `/api/bulk_generate` (대량 문제 생성)
```
🌐 HTTP Request
    ↓
📄 function_app.py (라우팅)
    ↓
🔧 services/bulk_service.py
    ├── 📊 questions_dim에서 4개 파라미터 세트 조회
    ├── 🤖 세트별 5개씩 총 20개 문제 생성
    ├── 🖼️ SVG 자동 생성 (도형/그래프 문제)
    └── 📤 JSON 응답 반환
```

### 3️⃣ `/api/create_question` (일반 문제 생성)
```
🌐 HTTP Request
    ↓
📄 function_app.py (라우팅)
    ↓
🔧 services/question_service.py
    ├── 📊 DB에서 문제 파라미터 조회
    ├── 🤖 AI 단일 문제 생성
    └── 📤 JSON 응답 반환
```

## 🧩 핵심 모듈 설명

### 📁 **core/** (공통 핵심 모듈)
- **database.py**: SQL Server 연결, 쿼리 실행, 캐싱
- **ai_service.py**: OpenAI API 호출, 프롬프트 생성, SVG 생성 로직
- **validation.py**: 생성된 문제 검증, DB 저장 레코드 준비
- **utils.py**: 학년 변환, ID 생성 등 유틸리티
- **responses.py**: 성공/실패 응답 표준화

### 📁 **services/** (비즈니스 로직)
- **view_service.py**: 뷰 기반 개인화 문제 생성
- **bulk_service.py**: 대량 문제 생성 (20개 배치)
- **question_service.py**: 일반 문제 생성 (단일)
- **connection_service.py**: DB/AI 연결 상태 테스트

### 📁 **handlers/** (API 핸들러)
- **create_by_view_handler.py**: Azure Functions 요청 처리

## 🎯 데이터 흐름 (create_by_view 예시)

```
1. 🔍 vw_personal_item_enriched 뷰 조회
   ↓ learnerID, assessmentItemID, knowledgeTag, grade, term,
     concept_name, difficulty_band 등

2. 🤖 각 요구사항별 AI 문제 생성
   ↓ 같은 concept_name끼리 중복 방지
   ↓ 난이도별 문제 길이 조절
   ↓ SVG 자동 생성 (도형/그래프 문제)

3. 📤 JSON 응답 생성
   ↓ assessmentItemID, question_text, choices,
     correct_answer, svg_content, metadata
```

## 🔧 환경 설정 도움말

자세한 환경 설정 방법은 [`README_환경설정.md`](./README_환경설정.md) 파일을 참고하세요.

## 🤝 기여하기

1. 이 저장소를 Fork
2. 새 기능 브랜치 생성 (`git checkout -b feature/새기능`)
3. 변경사항 커밋 (`git commit -m '새기능 추가'`)
4. 브랜치에 푸시 (`git push origin feature/새기능`)
5. Pull Request 생성

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

---

**💡 문의사항이나 버그 신고는 Issues 탭을 이용해주세요!**
