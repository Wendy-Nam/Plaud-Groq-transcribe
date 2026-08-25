# Plaud-Groq-Transcribe

**Plaud 음성 녹음기를 Groq Whisper로 자동 전사하는 파이프라인.** 회의·코칭·인터뷰 녹음을 한국어로 텍스트화하고, 필요 시 Google Drive에 저장합니다.

> 이 저장소는 **범용화(일반화)된 버전**입니다. 개인정보(이메일·계정·내부 경로)는 제거했습니다.

---

## 왜 좋은가 (핵심 가치)

- **무료** — Groq 무료 티어(`whisper-large-v3`)로 오디오 전사. OpenAI·별도 비용 없음.
- **한국어 정확성** — `language="ko"` 지정으로 한국어 회의·코칭·인터뷰 전사 정확도가 높습니다.
- **간단** — 표준 파이썬 표준 라이브러리만으로 동작(`requests` 조차 필수 아님), 설치 1줄.
- **실전 검증된 함정 해결 포함** — presigned URL 오염·Cloudflare 차단·용량 제한 대응 내장.
- **확장 가능** — 25MB 초과 자동 분할, 결과를 Google Drive에 저장.

한마디로: **"녹음하면 텍스트가 바로 나오는"** 회의·코칭·인터뷰 자동 기록 도구입니다.

---

## 구조

```
Plaud (list_files) → presigned_url → MP3 다운로드
        ↓
Groq Whisper (large-v3)  ← presigned URL 오염 주의
        ↓
전사 텍스트 (.txt) → (선택) Google Drive
```

---

## 설치

```bash
# Groq API 키 (무료 티어 발급: console.groq.com)
export GROQ_API_KEY="gsk_..."
```

파이썬 표준 라이브러리로 동작 — 별도 패키지 설치 불필요 (`requests`는 선택).

---

## 사용법 & 예제

### 준비
```bash
mkdir -p transcripts    # 전사본 저장 폴더 (필수 — 없으면 ENOENT)
```

### 파일 1개 전사 (기본 = 빠른 모델)
```bash
python3 groq_transcribe.py meeting.mp3
# → transcripts/meeting.txt  (1~2분 내 완료)
```

### 정확도 우선 + 출력 경로 지정
```bash
python3 groq_transcribe.py lecture.mp3 ./out/lecture.txt whisper-large-v3
```

### 실행 예시 (실제 입출력)

입력: `/audio/coaching1.mp3` (4.6MB / 14분)

```bash
python3 groq_transcribe.py /audio/coaching1.mp3
```

콘솔 출력:
```
오디오 크기: 4600000 bytes
전사 성공: 12,340자
저장: transcripts/coaching1.txt
```

생성된 `transcripts/coaching1.txt` 내용 (일부):

```
안녕하세요, 오늘 코칭 세션의 목표는...
```

---

## 함정 & 해결 (실전 검증)

### 1. presigned URL 오염 — 가장 빈번한 실패 원인
Plaud의 presigned URL은 **1,700자 이상**(대부분 `X-Amz-Security-Token`). 코드에 손으로 붙여넣으면 1글자만 틀려도 **HTTP 400/403**.

**정답**:
1. URL을 파일로 저장 (`url.txt`)
2. 다운로드: `curl -sL -o out.mp3 "$(cat url.txt)"`
3. 검증: `head -c3 out.mp3` → `ID3`이면 정상, `<?xml`/`<Error>`면 오염

### 2. Groq `file is empty` (간헐 오류)
Groq 세션 저하 또는 15MB 초과 파일에서 발생.
→ 1~2분 대기 후 재시도, 15MB 초과 시 10~15분 청크 분할, 최대 3회까지.

### 3. Groq 403 `error code: 1010` = Cloudflare UA 차단
오디오 업로드 엔드포인트가 기본 `urllib` UA를 차단. → 브라우저 UA 헤더 명시 (스크립트 내장).

### 4. 25MB Groq 제한
Plaud 코드 약 0.23MB/분 → 파일당 약 109분 한계.
→ `ffmpeg -c copy -segment_time 1200`로 20분 청크 분할.

---

## 라이선스
MIT

## 면책
개인 사용 목적으로 개발. Plaud·Groq 공식 제품 아님.