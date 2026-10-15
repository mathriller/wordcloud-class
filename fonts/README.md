# fonts 폴더 안내

이 앱은 그래프와 워드클라우드의 한글을 그릴 때 **이 폴더의 `NanumGothic.ttf`** 를 사용합니다.
컴퓨터(또는 서버)에 깔린 글꼴은 쓰지 않으므로, 이 파일이 꼭 있어야 합니다.

```
wordcloud/
├─ app.py
└─ fonts/
   ├─ NanumGothic.ttf   ← 꼭 이 이름
   ├─ OFL.txt           ← 글꼴 라이선스 원문
   └─ README.md         ← 지금 이 파일
```

## 글꼴이 없을 때 내려받아 넣는 방법

### 방법 1. Google Fonts에서 받기 (권장)
1. 웹브라우저에서 <https://fonts.google.com/specimen/Nanum+Gothic> 에 들어갑니다.
2. 오른쪽 위 **Get font → Download all** 을 눌러 zip 파일을 받습니다.
3. zip을 풀면 `NanumGothic-Regular.ttf` 가 있습니다.
4. 이 파일을 `fonts` 폴더에 넣고 이름을 **`NanumGothic.ttf`** 로 바꿉니다.
5. zip 안의 `OFL.txt` 도 함께 `fonts` 폴더에 넣습니다.

### 방법 2. 네이버 나눔글꼴 누리집에서 받기
1. <https://hangeul.naver.com/font> 에서 나눔고딕을 내려받아 설치 파일 또는 zip을 풉니다.
2. `NanumGothic.ttf` 파일을 찾아 이 `fonts` 폴더에 복사합니다.

> 파일 이름은 대·소문자까지 정확히 `NanumGothic.ttf` 여야 합니다.
> Streamlit Community Cloud(리눅스 서버)는 대·소문자를 구분합니다.

## 라이선스 (SIL Open Font License 1.1)

- 나눔고딕: Copyright (c) 2010, NHN Corporation, with Reserved Font Name Nanum, NanumGothic 등.
- 이 글꼴은 **SIL Open Font License, Version 1.1** 에 따라 배포됩니다.
  글꼴을 프로그램과 함께 자유롭게 사용·복사·재배포할 수 있으며, 글꼴 파일 자체를 단독으로 판매할 수는 없습니다.
- 재배포할 때는 라이선스 원문(`OFL.txt`)을 함께 둡니다. 원문: <https://openfontlicense.org>
