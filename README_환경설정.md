# Azure Functions 환경 설정 가이드

## 1. 가상환경 활성화

```bash
.venv\Scripts\Activate.ps1
```

## 2. local.settings.json 환경변수 설정

`local.settings.json` 파일에서 다음 값들을 실제 값으로 변경하세요:

### Azure OpenAI 설정

- `AOAI_KEY`: Azure OpenAI API 키
- `AOAI_ENDPOINT`: Azure OpenAI 엔드포인트 (예: https://your-resource.openai.azure.com/)
- `AOAI_DEPLOYMENT`: 배포된 모델 이름 (예: gpt-4, gpt-35-turbo)

### SQL Server 연결 설정

- `SQL_CONNECTION`: SQL Server 연결 문자열
  ```
  Driver={ODBC Driver 17 for SQL Server};Server=서버주소;Database=데이터베이스명;UID=사용자명;PWD=비밀번호;
  ```

## 3. 함수 실행

```bash
func start
```

## 4. API 엔드포인트

- 문제 생성: http://localhost:7071/api/create_question
- 연결 테스트: http://localhost:7071/api/test_connections
- 대량 생성: http://localhost:7071/api/bulk_generate

## 주의사항

- `local.settings.json`은 Git에 커밋되지 않습니다 (.gitignore에 포함)
- 실제 환경변수는 Azure Portal에서 Application Settings로 설정하세요
