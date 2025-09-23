# 📚 한국 중학교 수학 문제 생성 API

AI를 활용해 한국 중학교 수학 문제를 자동으로 생성하는 Azure Functions 서비스입니다.

## 🎯 프로젝트 목적

- **AI 기반 문제 생성**: Azure OpenAI GPT-4를 사용해 중학교 수준의 수학 문제 자동 생성
- **개인화 학습 지원**: 학습자별 맞춤형 문제 제공 (뷰 기반 및 learnerID 기반)
- **시각 자료 제공**: 기하, 그래프 문제에 정확한 SVG 이미지 자동 생성
- **데이터베이스 연동**: SQL Server에서 기존 문제 정보 및 학습자 데이터 활용
- **REST API 서비스**: 웹/앱에서 쉽게 사용할 수 있는 RESTful API 제공

## 🏗️ 프로젝트 구조

```
문제생성API2/
├── function_app.py                    # Azure Functions 메인 진입점
├── modules/
│   ├── handlers/                      # HTTP 요청 처리 계층
│   │   ├── create_by_view_handler.py  # 뷰 기반 문제 생성 핸들러
│   │   └── personalized_handler.py   # 개인화 문제 생성 핸들러
│   ├── services/                      # 비즈니스 로직 계층
│   │   ├── question_service.py       # 일반 문제 생성 서비스
│   │   ├── connection_service.py     # 연결 테스트 서비스
│   │   ├── bulk_service.py           # 대량 문제 생성 서비스
│   │   ├── view_service.py           # 뷰 기반 문제 생성 서비스
│   │   └── personalized_service.py   # 개인화 문제 생성 서비스
│   └── core/                          # 공통 유틸리티 계층
│       ├── ai_service.py             # AI 문제 생성 핵심 로직
│       ├── database.py               # 데이터베이스 연결 및 쿼리
│       ├── validation.py             # 문제 형식 검증
│       ├── responses.py              # HTTP 응답 형식 관리
│       ├── utils.py                  # 공통 유틸리티 함수
│       ├── params.py                 # 요청 파라미터 처리
│       └── debug.py                  # 디버깅 및 로깅
├── mapping/                           # 개념 매핑 유틸리티
└── scripts/                          # 추가 스크립트
```

## 🚀 API 엔드포인트

### 1. 📝 일반 문제 생성 - `/api/create_question`

**목적**: 지정된 조건에 맞는 수학 문제 1개를 생성합니다.

#### 📥 요청 방법
```http
GET /api/create_question?grade=2&term=1&topic_name=삼각형과 사각형&question_type=선택형&difficulty=중&count=1
```

#### 📋 파라미터
- `grade`: 학년 (1, 2, 3)
- `term`: 학기 (1, 2)
- `topic_name`: 주제명 (예: "삼각형과 사각형", "연립방정식")
- `question_type`: 문제 유형 ("선택형", "서술형")
- `difficulty`: 난이도 ("하", "중", "상")
- `count`: 생성할 문제 수 (기본값: 1)

#### 🔄 처리 과정
1. **파라미터 검증**: 필수 파라미터 확인 및 형식 검증
2. **기존 문제 조회**: 동일한 주제의 기존 문제들을 데이터베이스에서 가져와 중복 방지
3. **AI 문제 생성**: OpenAI GPT-4를 사용해 조건에 맞는 문제 생성
4. **형식 검증**: 생성된 문제가 올바른 JSON 형식인지 확인
5. **SVG 생성**: 필요한 경우 도형/그래프를 위한 SVG 이미지 생성
6. **응답 반환**: 검증된 문제를 JSON 형식으로 반환

#### 📤 응답 예시
```json
{
  "success": true,
  "generated_questions": [
    {
      "id": "Q_20241222_143022_ABC123",
      "question_text": "다음 중 이등변삼각형의 성질로 옳은 것은?",
      "question_type": "선택형",
      "choices": [
        "① 두 밑각의 크기가 같다",
        "② 세 변의 길이가 모두 같다",
        "③ 한 내각이 반드시 90°이다",
        "④ 외심과 내심이 일치한다",
        "⑤ 세 내각의 크기가 모두 같다"
      ],
      "correct_answer": "①",
      "answer_explanation": "이등변삼각형에서는 두 밑각의 크기가 항상 같습니다...",
      "svg_content": "<svg>...</svg>",
      "metadata": {
        "grade": "2",
        "term": "1",
        "topic_name": "삼각형과 사각형",
        "difficulty": "중"
      }
    }
  ]
}
```

---

### 2. 🔗 연결 테스트 - `/api/test_connections`

**목적**: Azure OpenAI와 SQL Server의 연결 상태를 확인합니다.

#### 📥 요청 방법
```http
GET /api/test_connections
```

#### 🔄 처리 과정
1. **OpenAI 연결 테스트**: Azure OpenAI 서비스에 간단한 요청을 보내 응답 확인
2. **SQL Server 연결 테스트**: 데이터베이스에 `SELECT 1` 쿼리 실행하여 연결 확인
3. **결과 요약**: 각 서비스의 연결 상태를 종합하여 보고

#### 📤 응답 예시
```json
{
  "openai_status": "✅ SUCCESS",
  "sql_status": "✅ SUCCESS",
  "status_code": 200
}
```

---

### 3. 🔢 대량 문제 생성 - `/api/bulk_generate`

**목적**: 여러 다른 조건으로 20개의 문제를 한 번에 생성합니다.

#### 📥 요청 방법
```http
GET /api/bulk_generate
```

#### 🔄 처리 과정
1. **파라미터 세트 조회**: `questions_dim` 테이블에서 서로 다른 4개의 파라미터 세트 조회
2. **세트별 문제 생성**: 각 파라미터 세트당 5개씩 문제 생성
3. **중복 방지**: 같은 세트 내에서 유사한 문제 생성 방지
4. **진행 상황 표시**: 터미널에 실시간 생성 진행 상황 출력
5. **개념 매핑**: 각 문제에 대해 concept_name과 knowledge_tag 자동 매핑

#### 📤 응답 예시
```json
{
  "success": true,
  "generated_questions": [
    {
      "id": "Q_20241222_143100_XYZ456",
      "source_id": 1,
      "question_text": "...",
      "metadata": {
        "grade": "1",
        "term": "2",
        "topic_name": "정수와 유리수",
        "difficulty": "하",
        "set_number": 1,
        "mapped_concept_name": "정수의 덧셈과 뺄셈",
        "knowledge_tag": "정수연산"
      }
    }
    // ... 총 20개 문제
  ],
  "summary": {
    "total_generated": 20,
    "target_count": 20,
    "sets_processed": 4,
    "questions_per_set": [5, 5, 5, 5]
  }
}
```

---

### 4. 📊 뷰 기반 문제 생성 - `/api/create_by_view`

**목적**: `vw_personal_item_enriched` 뷰에서 랜덤으로 5개 레코드를 선택해 개인화 문제를 생성합니다.

#### 📥 요청 방법
```http
GET /api/create_by_view
```

#### 🔄 처리 과정
1. **뷰 데이터 조회**: `vw_personal_item_enriched`에서 TOP 5 레코드 무작위 선택
2. **개인화 문제 생성**: 각 레코드의 학습자 정보에 맞는 문제 생성
3. **메타데이터 추가**: assessmentItemID, knowledgeTag 등 개인화 정보 포함
4. **중복 방지**: 같은 concept_name 내에서 유사한 문제 생성 방지

#### 📤 응답 예시
```json
{
  "success": true,
  "generated_questions": [
    {
      "id": "Q_20241222_143200_PQR789",
      "question_text": "...",
      "metadata": {
        "grade": "2",
        "term": "1",
        "concept_name": "일차방정식의 풀이",
        "chapter_name": "문자와 식",
        "difficulty_band": "중",
        "knowledge_tag": "방정식풀이",
        "mapped_concept_name": "일차방정식",
        "mapped_knowledge_tag": "방정식해법"
      }
    }
    // ... 총 5개 문제
  ],
  "summary": {
    "total_generated": 5,
    "total_requirements": 5,
    "concepts_covered": 4
  }
}
```

---

### 5. 👤 개인화 문제 생성 - `/api/create_personalized` ⭐ **최신 추가**

**목적**: 특정 learnerID의 모든 학습 요구사항에 맞는 개인화 문제를 생성합니다.

#### 📥 요청 방법
```http
GET /api/create_personalized?learnerID=12345
```

#### 📋 파라미터
- `learnerID` (필수): 학습자 고유 ID

#### 🔄 처리 과정
1. **학습자 데이터 조회**: 해당 learnerID의 모든 데이터를 `vw_personal_item_enriched`에서 조회
2. **데이터 개수 확인**: 실제 존재하는 레코드 수만큼 문제 생성 (동적 개수)
3. **개인화 문제 생성**: 각 요구사항에 정확히 맞는 문제 생성
4. **학습 히스토리 반영**: 해당 학습자의 assessmentItemID와 knowledgeTag 기반 맞춤 생성
5. **성공률 추적**: 생성 성공률과 커버된 개념 수 계산

#### 📤 응답 예시
```json
{
  "success": true,
  "generated_questions": [
    {
      "id": "Q_20241222_143300_STU123",
      "learner_id": "12345",
      "assessment_item_id": "ITEM_001",
      "question_text": "다음 일차방정식을 풀어보세요: 3x + 7 = 16",
      "question_type": "선택형",
      "choices": ["① x = 3", "② x = 4", "③ x = 5", "④ x = 6", "⑤ x = 7"],
      "correct_answer": "①",
      "answer_explanation": "3x + 7 = 16에서 3x = 9, 따라서 x = 3입니다.",
      "metadata": {
        "grade": "1",
        "term": "2",
        "concept_name": "일차방정식의 풀이",
        "chapter_name": "문자와 식",
        "topic_name": "방정식",
        "unit_name": "문자와 식의 계산",
        "difficulty_band": "중",
        "knowledge_tag": "방정식풀이",
        "mapped_concept_name": "일차방정식",
        "mapped_knowledge_tag": "방정식해법"
      }
    }
    // ... 해당 학습자의 모든 요구사항만큼 문제 생성
  ],
  "summary": {
    "learner_id": "12345",
    "total_generated": 6,
    "total_requirements": 6,
    "success_rate": 100.0,
    "concepts_covered": 4
  }
}
```

#### 💡 사용 사례
- **학습자 접속 시**: 개인 맞춤 문제 세트 제공
- **복습 문제 생성**: 약한 부분 집중 문제 제공
- **진도별 문제**: 학습 진행 상황에 맞는 문제 생성

---

## 🛠️ 기술 스택

### 백엔드
- **Azure Functions**: 서버리스 API 서비스
- **Python 3.8+**: 메인 개발 언어
- **Azure OpenAI (GPT-4)**: AI 문제 생성 엔진
- **pyodbc**: SQL Server 데이터베이스 연결

### 프론트엔드 지원
- **RESTful API**: 표준 HTTP 메서드 지원
- **JSON 응답**: 웹/앱에서 쉬운 파싱
- **CORS 지원**: 크로스 도메인 요청 허용

### 시각화
- **SVG**: 수학 도형/그래프 벡터 이미지
- **LaTeX**: 수학 공식 표현
- **반응형 디자인**: 태블릿/모바일 최적화

## 📋 환경 설정

### 필요 조건
- Python 3.8+
- Azure Functions Core Tools
- Azure OpenAI 서비스 구독
- SQL Server 데이터베이스

### 환경 변수
```env
AOAI_ENDPOINT=https://your-openai-endpoint.openai.azure.com/
AOAI_KEY=your-azure-openai-key
AOAI_DEPLOYMENT=gpt-4o-create_question
SQL_CONNECTION=Driver={ODBC Driver 17 for SQL Server};Server=your-server;Database=your-db;UID=your-username;PWD=your-password;
```

### 설치 및 실행
```bash
# 의존성 설치
pip install -r requirements.txt

# 로컬 실행
func start

# 클라우드 배포
func azure functionapp publish your-function-app-name
```

## 🎯 주요 특징

### 1. 🧠 지능형 문제 생성
- **컨텍스트 인식**: 기존 문제와 중복되지 않는 새로운 문제 생성
- **난이도 조절**: 쉬움(1-2문장), 중간(3문장), 어려움(4문장)으로 자동 조절
- **LaTeX 지원**: 복잡한 수학 공식도 정확하게 표현

### 2. 📐 정확한 시각 자료
- **문제-그림 일치**: AI가 문제 내용과 완벽히 일치하는 SVG 생성
- **각도 표현 개선**: 시각적 추정 대신 알파벳 라벨(∠ABC) 사용으로 정확도 향상
- **반응형 SVG**: 다양한 화면 크기에 자동 대응

### 3. 🎯 개인화 학습
- **learnerID 기반**: 개별 학습자의 요구사항에 정확히 맞춤
- **동적 문제 수**: 학습자 데이터만큼 유연하게 문제 생성
- **학습 진도 반영**: assessmentItemID와 knowledgeTag 기반 맞춤 생성

### 4. 🔄 모듈러 아키텍처
- **3계층 구조**: Handlers(HTTP) → Services(비즈니스) → Core(유틸리티)
- **코드 재사용**: 공통 기능의 모듈화로 중복 제거
- **확장 가능**: 새로운 기능 추가 시 기존 모듈 재활용

## 🚀 사용 예시

### 웹 애플리케이션에서 사용
```javascript
// 개인화 문제 가져오기
const response = await fetch('/api/create_personalized?learnerID=12345');
const data = await response.json();

// 생성된 문제들 표시
data.generated_questions.forEach(question => {
    displayQuestion(question);
});
```

### 모바일 앱에서 사용
```dart
// Flutter 예시
Future<List<Question>> getPersonalizedQuestions(String learnerId) async {
  final response = await http.get(
    Uri.parse('$baseUrl/api/create_personalized?learnerID=$learnerId')
  );

  final data = json.decode(response.body);
  return data['generated_questions'].map((q) => Question.fromJson(q)).toList();
}
```

## 📊 성능 및 제한사항

### 성능
- **응답 시간**: 문제 1개당 평균 3-5초
- **대량 생성**: 20개 문제 약 60-100초
- **동시 요청**: Azure Functions 자동 스케일링 지원

### 제한사항
- **API 호출 제한**: Azure OpenAI 서비스 할당량에 따름
- **문제 품질**: AI 생성 특성상 간헐적 검토 필요
- **SVG 복잡도**: 매우 복잡한 3D 도형은 제한적

## 🔧 문제 해결

### 자주 발생하는 오류

1. **JSON 파싱 오류**
   - **원인**: LaTeX 수식의 백슬래시 이스케이프 문제
   - **해결**: 자동 백슬래시 처리 로직 적용됨

2. **연결 오류**
   - **원인**: 환경 변수 설정 문제
   - **해결**: `/api/test_connections`로 연결 상태 확인

3. **문제 생성 실패**
   - **원인**: AI 서비스 일시적 오류
   - **해결**: 재시도 로직 및 백업 파싱 적용됨

## 📈 향후 계획

- [ ] 문제 난이도 자동 조절 알고리즘 개선
- [ ] 더 다양한 문제 유형 지원 (증명, 작도 등)
- [ ] 실시간 문제 품질 평가 시스템
- [ ] 학습자 피드백 기반 개인화 강화
- [ ] 멀티미디어 요소 추가 (동영상 해설 등)

## 🤝 기여 방법

1. 이 저장소를 포크합니다
2. 새 기능 브랜치를 만듭니다 (`git checkout -b feature/새기능`)
3. 변경사항을 커밋합니다 (`git commit -m '새 기능 추가'`)
4. 브랜치에 푸시합니다 (`git push origin feature/새기능`)
5. Pull Request를 생성합니다

## 📞 문의 및 지원

- **GitHub Issues**: 버그 리포트 및 기능 요청
- **이메일**: [개발자 이메일]
- **문서**: 이 README 파일 및 코드 주석 참조

---

> 🎓 **교육용 프로젝트**: 이 프로젝트는 한국 중학교 수학 교육을 위해 개발되었습니다.
>
> 🚀 **지속적 개선**: AI 기술과 교육 방법론의 발전에 따라 지속적으로 업데이트됩니다.