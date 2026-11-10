# 감정서랍 (Emotion Drawer)

상황 → 생각 → 감정 → 욕구 4단계 질문으로 감정을 기록하고 돌아보는 웹앱과 그 랜딩페이지.
가상 서비스이며, 수업(AGM) 프로젝트로 로컬에서 먼저 완성한다.

## 문서

- **작업 로그·인수인계: `WORKLOG.md` (새 대화나 다른 AI는 이 문서부터 읽을 것)**
- 요구사항: `PRD/감정서랍_PRD_v3.md` (v1·v2는 참고용 이전 판). 화면 문구 전체 목록은 v3 11장
- 구현 계획: `PLAN.md`
- 원본 기획서: `감정서랍_브랜드_성장전략_통합기획2.md` (로컬에만 보관, 저장소에는 올리지 않음)

## 폴더 구조

```text
agm_last_project/
├─ WORKLOG.md           작업 로그·인수인계
├─ CLAUDE.md
├─ PLAN.md
├─ PRD/                 요구사항 문서 (판 번호를 올려 새 파일로 저장)
├─ backup/              단계 시작 전 백업 (backup/날짜_N단계전/)
└─ emotion_drawer/      Flask 웹앱 (구조는 PLAN.md 참고)
```

## 실행 방법

```bash
cd emotion_drawer
pip install -r requirements.txt
python init_db.py
python app.py
```

브라우저에서 http://localhost:5000 을 연다. (`run.bat` 더블클릭으로도 실행)

## 프로젝트 공통 규칙

- 요구사항의 기준은 `PRD/감정서랍_PRD_v3.md`다. PRD에 없는 기능은 만들지 말고 먼저 물어볼 것.
- 웹 서버는 Python Flask로 만든다. 웹앱은 `emotion_drawer` 폴더, 포트 5000.
- 화면은 Jinja 템플릿 + 순수 CSS·JavaScript로 만든다. npm 같은 빌드 도구는 쓰지 않는다.
- 데이터베이스는 SQLite 파일 하나만 쓴다. 로컬은 `emotion_drawer/emotion_drawer.db`, 배포(Railway)는 `DATABASE_PATH`로 지정한 Volume 안의 파일(`/data/emotion_drawer.db`). 테이블 구조는 PRD 5장을 따른다.
- 비밀번호는 평문으로 저장하지 말고 해시로 저장할 것.
- 화면 안내 문구는 PRD에 적힌 문장을 그대로 쓸 것. 말투는 해요체.
- 감정·욕구 목록은 코드에 고정하지 말고 항상 DB(`emotions`, `needs`)에서 읽을 것.
- 기록을 조회·수정·삭제할 때는 항상 서버에서 로그인한 사용자의 기록인지 확인할 것 (`WHERE id = ? AND user_id = ?`). 아니면 404.
- Plus 여부는 화면뿐 아니라 서버에서도 매 요청마다 확인할 것.
- 체험(`/try`) 기록은 사용자가 [보관하기]를 누르기 전까지 서버로 보내지 말 것.
- GA4 이벤트·서버 로그·URL에 기록 내용, 감정 이름, 이메일을 넣지 말 것.
- 비밀 키와 GA4 측정 ID는 `.env`에서만 읽는다. 코드에 직접 쓰지 말고, `.env`는 공유하지 말 것 (`.env.example`만 공유).
- 감정을 좋음/나쁨, 긍정/부정으로 나누는 표현이나 색을 쓰지 말 것. 회고 문장은 원인이나 사람을 단정하지 말 것.
- 날짜와 시간은 한국 시간(Asia/Seoul) 기준.
- 반드시 한 단계씩 진행하고, 단계가 끝나면 브라우저로 확인할 방법과 충족한 PRD 9장 완료 기준을 알려 줄 것.
- 새 단계를 시작하기 전에 `emotion_drawer` 폴더와 DB를 `backup/날짜_N단계전/`에 복사할 것.
- 단계가 끝나거나 중요한 결정을 하면 `WORKLOG.md`를 갱신할 것: '0. 인수인계 요약'의 현재 진행·다음 할 일, '4. 작업 기록'에 한 항목(만든 것·확인한 것·고친 것), 필요하면 '2-2 결정'과 '3. 확인하지 못한 것'.
