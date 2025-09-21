# 📚 한국 중학교 수학 문제 생성기

AI를 활용해 한국 중학교 수학 문제를 자동으로 생성하는 Azure Functions 서비스입니다.

## 🎯 프로젝트 목적

- **AI 문제 생성**: GPT-4를 사용해 중학교 수준의 수학 문제 자동 생성
- **시각 자료 제공**: 기하, 그래프 문제에 SVG 이미지 자동 생성
- **데이터베이스 연동**: SQL Server에서 기존 문제 정보를 가져와 학습에 활용
- **REST API 제공**: 웹/앱에서 쉽게 사용할 수 있는 API 서비스

## 🚀 주요 기능

### 1. 문제 생성 (`/api/create_question`)
- 주제별 맞춤 문제 생성
- 선택형/서술형 문제 지원
- 자동 SVG 이미지 생성 (기하, 그래프 문제)
- LaTeX 수식 지원

### 2. 대량 생성 (`/api/bulk_generate`)
- 여러 문제를 한 번에 생성
- 배치 처리로 효율적인 생성

### 3. 연결 테스트 (`/api/test_connections`)
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

### 문제 생성 요청
```http
POST http://localhost:7071/api/create_question
Content-Type: application/json

{
  "topic_name": "이차함수"
}
```

### 응답 예시
```json
{
  "question_text": "이차함수 y = x² - 2x + 1의 그래프를 그리시오.",
  "question_type": "선택형",
  "choices": ["① 위로 볼록", "② 아래로 볼록", "③ 직선", "④ 원", "⑤ 타원"],
  "correct_answer": "②",
  "answer_explanation": "a = 1 > 0이므로 포물선이 아래로 볼록합니다.",
  "svg_code": "<svg width='300' height='200'>...</svg>"
}
```

## 🎨 SVG 이미지 기능

다음 유형의 문제에서 자동으로 시각 자료가 생성됩니다:
- 📐 기하 문제 (삼각형, 사각형, 원 등)
- 📊 함수 그래프 (일차함수, 이차함수)
- 📈 통계 차트 (막대그래프, 원그래프)
- 📏 좌표 평면 문제

## 📁 프로젝트 구조

```
creaet_question/
├── function_app.py          # 메인 API 앱
├── host.json               # Azure Functions 설정
├── requirements.txt        # Python 패키지 목록
├── start.bat              # 실행 스크립트
├── local.settings.json    # 환경 변수 (로컬용)
├── modules/               # 핵심 로직
│   ├── ai_service.py      # AI 문제 생성
│   ├── database.py        # 데이터베이스 연결
│   ├── question_service.py # 문제 생성 서비스
│   ├── bulk_service.py    # 대량 생성 서비스
│   └── connection_service.py # 연결 테스트 서비스
└── .venv/                 # Python 가상환경
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
