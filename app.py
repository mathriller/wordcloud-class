"""
자연어 처리 → 단어 빈도 → 워드클라우드 실습 앱
(초등수학영재프로그램개발 강좌용 교육 도구)

실행: streamlit run app.py
- 입력한 텍스트는 서버에 저장하지 않고, 접속한 사람의 세션 안에서만 사용합니다.
"""

import html
import io
import math
import random
import re
import threading
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib import font_manager
from matplotlib.ticker import MaxNLocator
from PIL import Image

# ──────────────────────────────────────────────────────────────
# 기본 설정
# ──────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent
FONT_PATH = APP_DIR / "fonts" / "NanumGothic.ttf"
FONT_OK = FONT_PATH.exists()
MAX_CHARS = 200_000  # 너무 긴 글은 서버가 힘들어하므로 앞부분만 분석

st.set_page_config(page_title="워드클라우드 실습실", page_icon="☁️", layout="wide")

# 품사 코드 → 한국어 이름, 기본 체크 여부
POS_OPTIONS = [
    ("NNG", "일반명사", True),
    ("NNP", "고유명사", True),
    ("VV", "동사", False),
    ("VA", "형용사", False),
    ("MAG", "부사", False),
    ("SL", "외국어", False),
]
POS_NAMES = {code: name for code, name, _ in POS_OPTIONS}

DEFAULT_STOPWORDS = "있다, 하다, 되다, 것, 수, 등, 이다, 않다, 없다"
DEFAULT_USERWORDS = "워드클라우드, 생성형AI"

# 명사 뒤에 붙어 동사·형용사를 만드는 접미사(추천+하다, 사용+되다 …)
VERB_SUFFIXES = {"하", "되", "시키"}

EXAMPLES = {
    "예시 1: 영화 댓글": {
        "text": (
            "이 영화는 긴장감과 감동이 있는 영화예요.\n\n"
            "이 영화는 감동은 있지만 지루해서 실망이에요.\n\n"
            "추천! 눈물 없이는 볼 수 없는 감동적인 영화입니다."
        ),
        "pos": {"NNG": True, "NNP": True, "VV": True, "VA": True, "MAG": False, "SL": False},
        "split": False,
        "userwords": DEFAULT_USERWORDS,
        "note": "명사·동사·형용사를 포함하고 불용어는 기본값으로 맞췄어요.",
    },
    "예시 2: 청바지 후기": {
        "text": (
            "청바지 추천! 예쁘고 저렴해서 청바지를 추천해요.\n\n"
            "청바지의 가격, 디자인 다 좋아요. 특히 디자인 추천!^^\n\n"
            "신축성과 디자인이 좋고, 가격도 좋아서 이 청바지를 추천해요."
        ),
        "pos": {"NNG": True, "NNP": True, "VV": False, "VA": True, "MAG": False, "SL": False},
        "split": True,
        "userwords": DEFAULT_USERWORDS + ", 신축성",
        "note": (
            "명사·형용사를 포함하고 '문서 나누기'를 켰어요. "
            "사용자 사전에 '신축성'을 넣어 두었어요. 지우면 '신축+성'으로 나뉘는 것을 볼 수 있어요."
        ),
    },
}

COLORMAPS = {
    "차분한 파랑·초록 (viridis)": "viridis",
    "보라·주황 (plasma)": "plasma",
    "알록달록 (tab10)": "tab10",
    "파스텔 (Set2)": "Set2",
    "진한 색 (Dark2)": "Dark2",
    "파랑↔빨강 (coolwarm)": "coolwarm",
    "단색 (직접 고르기)": None,
}
BACKGROUNDS = {"흰색": "white", "검정": "black", "투명": None}

# ──────────────────────────────────────────────────────────────
# 화면 꾸미기 (프로젝터용 큰 글씨)
# ──────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
html, body, [data-testid="stAppViewContainer"] { font-size: 19px; }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li { font-size: 1.08rem; }
textarea { font-size: 1.15rem !important; line-height: 1.6 !important; }
.app-title { font-size: 2.3rem; font-weight: 800; margin: 0 0 .2rem 0; }
.app-sub { font-size: 1.1rem; color: #4A5568; margin-bottom: 1rem; }
.step-head { display: flex; align-items: center; gap: .8rem; margin: 2.4rem 0 .5rem 0; }
.step-num {
  flex: none; width: 3rem; height: 3rem; border-radius: 50%;
  background: #2F6DB5; color: #fff; font-size: 1.6rem; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
}
.step-title { font-size: 2rem; font-weight: 800; color: #1A2B44; }
.step-desc {
  background: #EEF4FB; border-left: 6px solid #2F6DB5; border-radius: 6px;
  padding: .7rem 1.1rem; font-size: 1.15rem; margin-bottom: 1rem; color: #1A2B44;
}
.chips { line-height: 2.6; margin: .2rem 0 .9rem 0; }
.chip {
  display: inline-block; padding: .05rem .45rem; margin: 0 .15rem; border-radius: 6px;
  background: #F1F3F6; color: #8A94A6; border: 1px solid #E2E6EC; font-size: 1.05rem;
}
.chip sub { font-size: .65rem; margin-left: .15rem; }
.chip.on { background: #DCEBFA; color: #123B6D; border-color: #9CC3EC; font-weight: 700; }
.chip.stop { background: #FDECEC; color: #9B2C2C; border-color: #F5B5B5; text-decoration: line-through; }
.legend span { margin-right: 1rem; }
</style>
""",
    unsafe_allow_html=True,
)


def step_header(num: str, title: str, desc: str) -> None:
    st.markdown(
        f'<div class="step-head"><div class="step-num">{num}</div>'
        f'<div class="step-title">{title}</div></div>'
        f'<div class="step-desc">{desc}</div>',
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────
# 세션 상태 초기값
# ──────────────────────────────────────────────────────────────
ss = st.session_state
_defaults = {
    "text": "",
    "split": False,
    "one_char": False,
    "stopwords": DEFAULT_STOPWORDS,
    "userwords": DEFAULT_USERWORDS,
    "renames": {},  # 원래 단어 → 고친 단어
    "excluded": set(),  # 표에서 [포함]을 끈 단어
    "editor_ver": 0,  # 표를 새로 그릴 때마다 올림
    "wc_seed": 42,
    "example_choice": list(EXAMPLES)[0],
    "example_note": "",
}
for k, v in _defaults.items():
    ss.setdefault(k, v)
for code, _, default in POS_OPTIONS:
    ss.setdefault(f"pos_{code}", default)


def reset_edits() -> None:
    ss.renames = {}
    ss.excluded = set()
    ss.editor_ver += 1


def load_example() -> None:
    ex = EXAMPLES[ss.example_choice]
    ss.text = ex["text"]
    ss.split = ex["split"]
    ss.userwords = ex["userwords"]
    ss.stopwords = DEFAULT_STOPWORDS
    for code, on in ex["pos"].items():
        ss[f"pos_{code}"] = on
    ss.example_note = f"「{ss.example_choice}」을 불러왔어요. {ex['note']}"
    reset_edits()


def decode_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def load_uploaded_file() -> None:
    f = ss.get("uploaded_txt")
    if f is None:
        return
    ss.text = decode_bytes(f.getvalue())
    ss.example_note = f"파일 「{f.name}」을 불러왔어요."
    reset_edits()


def split_list(s: str) -> list[str]:
    return [w.strip() for w in re.split(r"[,\n]", s) if w.strip()]


# ──────────────────────────────────────────────────────────────
# 형태소 분석 (Kiwi)
# ──────────────────────────────────────────────────────────────
class KiwiBox:
    """Kiwi 한 개를 모든 접속자가 함께 쓰기 위한 상자."""

    def __init__(self):
        from kiwipiepy import Kiwi

        # 오타 교정·다어절 사전은 이 실습에 필요 없어 꺼서 메모리를 아낀다.
        self.kiwi = Kiwi(load_typo_dict=False, load_multi_dict=False)
        self.lock = threading.Lock()
        self.added: set[str] = set()  # add_user_word로 추가된 단어 전체


@st.cache_resource(show_spinner="형태소 분석기(Kiwi)를 준비하는 중이에요…")
def get_kiwi() -> KiwiBox:
    return KiwiBox()


def valid_user_word(w: str) -> bool:
    return 2 <= len(w) <= 20 and not re.search(r"\s", w)


@st.cache_data(show_spinner=False, max_entries=64)
def tokenize_lines(lines: tuple[str, ...], user_words: tuple[str, ...]) -> list[list[tuple[str, str, str]]]:
    """줄마다 Kiwi로 형태소 분석 → [(형태, 품사, 기본형), …] 목록."""
    from kiwipiepy import MorphemeSet

    box = get_kiwi()
    with box.lock:
        for w in user_words:
            if w not in box.added and box.kiwi.add_user_word(w, "NNP", 0):
                box.added.add(w)
        # Kiwi는 하나를 함께 쓰므로, 다른 사람이 넣은 사용자 단어는 이번 분석에서 막아 둔다.
        others = [(w, "NNP") for w in box.added if w not in user_words]
        blocklist = MorphemeSet(box.kiwi, others) if others else None
        result = []
        for line in lines:
            tokens = box.kiwi.tokenize(line, blocklist=blocklist)
            result.append([(t.form, t.tag, getattr(t, "lemma", None) or t.form) for t in tokens])
    return result


def normalize(tokens: list[tuple[str, str, str]]) -> list[tuple[str, str, list[int]]]:
    """형태소 목록을 '셀 단어' 목록으로 바꾼다. → [(단어, 품사, 원래 형태소 번호들), …]

    - 동사·형용사는 기본형(어간+다): 볼 → 보다, 좋아요 → 좋다
    - 어근(XR)+하다: 지루+하 → 지루하다(형용사)
    - 명사 뒤 '하/되/시키'(XSV·XSA): 추천+하 → 추천, 하다
    """
    out = []
    i = 0
    while i < len(tokens):
        form, tag, lemma = tokens[i]
        base = tag.split("-")[0]  # VV-I(불규칙) → VV
        nxt_base = tokens[i + 1][1].split("-")[0] if i + 1 < len(tokens) else ""
        if base == "XR" and nxt_base in ("XSA", "XSV"):
            word = form + tokens[i + 1][0] + "다"
            out.append((word, "VA" if nxt_base == "XSA" else "VV", [i, i + 1]))
            i += 2
            continue
        if base in ("VV", "VA"):
            word = lemma if lemma.endswith("다") else form + "다"
            out.append((word, base, [i]))
        elif base in ("XSV", "XSA") and form in VERB_SUFFIXES:
            out.append((form + "다", "VV" if base == "XSV" else "VA", [i]))
        else:
            out.append((form, base, [i]))
        i += 1
    return out


# ──────────────────────────────────────────────────────────────
# 빈도표 편집 (이름 고치기·포함 끄기)를 세션 상태로 관리
# ──────────────────────────────────────────────────────────────
def pos_label(codes) -> str:
    seen = list(dict.fromkeys(codes))
    return ", ".join(f"{POS_NAMES.get(c, c)}({c})" for c in seen)


def build_table(base: pd.DataFrame) -> pd.DataFrame:
    """분석 결과(base)에 이름 고치기·제외를 적용해 화면용 빈도표를 만든다."""
    cols = ["포함", "단어", "품사", "빈도", "상대도수"]
    if base.empty:
        return pd.DataFrame(columns=cols)
    df = base.copy()
    df["단어"] = df["단어"].map(lambda w: ss.renames.get(w, w))
    g = (
        df.groupby("단어", sort=False)
        .agg(품사=("품사", pos_label), 빈도=("빈도", "sum"))
        .reset_index()
    )
    g["상대도수"] = g["빈도"] / g["빈도"].sum()
    g["포함"] = ~g["단어"].isin(ss.excluded)
    g = g.sort_values(["빈도", "단어"], ascending=[False, True]).reset_index(drop=True)
    return g[cols]


def rename_word(old: str, new: str) -> None:
    """화면의 단어 old를 new로 바꾼다. 같은 이름이 있으면 빈도가 합쳐진다."""
    originals = set(ss.get("_base_words", [])) | set(ss.renames)
    for o in originals:
        if ss.renames.get(o, o) == old:
            if o == new:
                ss.renames.pop(o, None)
            else:
                ss.renames[o] = new


def on_table_edit(editor_key: str) -> None:
    shown: pd.DataFrame = ss["_shown_table"]
    edits = ss[editor_key].get("edited_rows", {})
    existing = set(shown["단어"])
    for idx, change in edits.items():
        row = shown.iloc[int(idx)]
        old = row["단어"]
        new = str(change.get("단어", old)).strip() or old
        if new != old:
            target_exists = new in existing
            rename_word(old, new)
            if old in ss.excluded:
                ss.excluded.discard(old)
                if not target_exists:
                    ss.excluded.add(new)
        if "포함" in change:
            if change["포함"]:
                ss.excluded.discard(new)
            else:
                ss.excluded.add(new)
    ss.editor_ver += 1  # 합쳐진 표로 새로 그리기


def include_all() -> None:
    ss.excluded = set()
    ss.editor_ver += 1


def include_top_n() -> None:
    shown: pd.DataFrame = ss["_shown_table"]
    n = int(ss.top_n_keep)
    ss.excluded = set(shown["단어"].iloc[n:])
    ss.editor_ver += 1


# ──────────────────────────────────────────────────────────────
# 그림 그리기
# ──────────────────────────────────────────────────────────────
if FONT_OK:
    font_manager.fontManager.addfont(str(FONT_PATH))
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(FONT_PATH)).get_name()
plt.rcParams["axes.unicode_minus"] = False


def make_mask(shape: str, upload: bytes | None):
    if shape == "사각형":
        return None
    if shape == "원":
        n = 900
        y, x = np.ogrid[:n, :n]
        c = (n - 1) / 2
        inside = (x - c) ** 2 + (y - c) ** 2 <= (n * 0.48) ** 2
        return np.where(inside, 0, 255).astype(np.uint8)
    if shape == "하트":
        n = 900
        xs = np.linspace(-1.35, 1.35, n)
        ys = np.linspace(1.45, -1.25, n)  # 그림은 위에서 아래로 그려지므로 y를 뒤집는다
        x, y = np.meshgrid(xs, ys)
        inside = (x**2 + y**2 - 1) ** 3 - x**2 * y**3 <= 0
        return np.where(inside, 0, 255).astype(np.uint8)
    if shape == "마스크 이미지" and upload:
        img = Image.open(io.BytesIO(upload)).convert("RGBA")
        img.thumbnail((1000, 1000))
        white = Image.new("RGBA", img.size, (255, 255, 255, 255))
        gray = np.array(Image.alpha_composite(white, img).convert("L"))
        return np.where(gray > 200, 255, 0).astype(np.uint8)  # 흰 부분 = 비워 둘 곳
    return None


@st.cache_data(show_spinner="워드클라우드를 그리는 중이에요…", max_entries=32)
def draw_wordcloud(freqs: tuple, opts: tuple, mask_upload: bytes | None) -> bytes:
    from wordcloud import WordCloud

    o = dict(opts)
    bg = BACKGROUNDS[o["bg"]]
    kwargs = dict(
        font_path=str(FONT_PATH),
        width=1200,
        height=800,
        mask=make_mask(o["shape"], mask_upload),
        max_words=o["max_words"],
        min_font_size=o["min_font"],
        max_font_size=o["max_font"],
        prefer_horizontal=o["horizontal"],
        relative_scaling=o["rel_scaling"],
        random_state=o["seed"],
        background_color=bg,
        mode="RGBA" if bg is None else "RGB",
        margin=4,
    )
    if o["colormap"]:
        kwargs["colormap"] = o["colormap"]
    else:
        color = o["single_color"]
        kwargs["color_func"] = lambda *a, **k: color
    wc = WordCloud(**kwargs).generate_from_frequencies(dict(freqs))
    buf = io.BytesIO()
    wc.to_image().save(buf, format="PNG")
    return buf.getvalue()


def draw_bar_chart(words: list[str], values: list[float], xlabel: str) -> bytes:
    n = len(words)
    fig, ax = plt.subplots(figsize=(10, max(3.0, 0.48 * n + 1)), dpi=150)
    y = np.arange(n)
    ax.barh(y, values, color="#2F6DB5")
    ax.set_yticks(y, words, fontsize=14)
    ax.invert_yaxis()  # 1등이 맨 위
    ax.set_xlabel(xlabel, fontsize=14)
    ax.tick_params(axis="x", labelsize=12)
    if all(float(v).is_integer() for v in values):
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    vmax = max(values) if values else 1
    for yi, v in zip(y, values):
        label = f"{v:g}" if float(v).is_integer() else f"{v:.2f}"
        ax.text(v + vmax * 0.01, yi, label, va="center", fontsize=13)
    ax.set_xlim(0, vmax * 1.12)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def fmt_num(x) -> str:
    if pd.isna(x):
        return ""
    if float(x).is_integer():
        return f"{int(x)}"
    return f"{x:.3f}".rstrip("0").rstrip(".")


# ══════════════════════════════════════════════════════════════
# 화면 시작
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="app-title">☁️ 워드클라우드 실습실</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-sub">글 → 형태소 분석 → 단어 빈도 → 워드클라우드, 세 단계로 따라가 보세요. '
    "입력한 글은 서버에 저장되지 않아요.</div>",
    unsafe_allow_html=True,
)

if not FONT_OK:
    st.error(
        "한글 글꼴 파일을 찾지 못했어요: `fonts/NanumGothic.ttf`\n\n"
        "나눔고딕(NanumGothic.ttf)을 내려받아 `fonts` 폴더에 넣은 뒤 앱을 다시 실행해 주세요. "
        "방법은 `fonts/README.md`에 있어요. 글꼴이 없으면 그래프와 워드클라우드의 한글이 □로 깨집니다."
    )

# ── 사이드바: 분석 옵션 ───────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 분석 옵션")
    st.markdown("**포함할 품사**")
    for code, name, _ in POS_OPTIONS:
        st.checkbox(f"{name} ({code})", key=f"pos_{code}")
    st.caption("동사·형용사는 기본형(어간+다)으로 보여 줘요. 예: 지루해서 → 지루하다, 볼 → 보다")
    st.checkbox("한 글자 단어 빼기", key="one_char")
    st.text_area(
        "불용어 (쉼표로 구분)",
        key="stopwords",
        height=110,
        help="세지 않을 단어예요. 기본형으로 적어 주세요(예: 있다, 하다).",
    )
    st.text_area(
        "사용자 사전 (쉼표로 구분)",
        key="userwords",
        height=90,
        help="붙여서 한 단어로 읽어야 할 말을 넣어요. 띄어쓰기 없이 2글자 이상. Kiwi의 add_user_word로 등록돼요.",
    )
    if st.button("옵션 처음 값으로", width="stretch"):
        ss.stopwords = DEFAULT_STOPWORDS
        ss.userwords = DEFAULT_USERWORDS
        ss.one_char = False
        for code, _, default in POS_OPTIONS:
            ss[f"pos_{code}"] = default
        st.rerun()

# ══════════════════════════════════════════════════════════════
# ① 텍스트 입력
# ══════════════════════════════════════════════════════════════
step_header("①", "텍스트 입력", "분석할 글을 넣어요. 직접 붙여 넣거나, .txt 파일을 올리거나, 예시를 불러올 수 있어요.")

c1, c2 = st.columns([3, 2], gap="large")
with c2:
    st.selectbox("예시 고르기", list(EXAMPLES), key="example_choice")
    st.button("📥 예시 불러오기", on_click=load_example, type="primary", width="stretch")
    st.file_uploader(
        "또는 .txt 파일 올리기 (UTF-8, CP949 모두 가능)",
        type=["txt"],
        key="uploaded_txt",
        on_change=load_uploaded_file,
    )
    st.toggle(
        "문서 나누기 (빈 줄 기준)",
        key="split",
        help="켜면 빈 줄로 구분된 덩어리를 각각 하나의 문서로 봐요. TF-IDF를 계산할 때 필요해요.",
    )
with c1:
    st.text_area(
        "분석할 글",
        key="text",
        height=300,
        placeholder="여기에 글을 붙여 넣으세요.\n\n'문서 나누기'를 켜면 빈 줄로 문서를 구분해요.",
    )
if ss.example_note:
    st.info(ss.example_note)

text = ss.text[:MAX_CHARS]
if len(ss.text) > MAX_CHARS:
    st.warning(f"글이 너무 길어서 앞의 {MAX_CHARS:,}자만 분석해요.")

if ss.split:
    docs = [d.strip() for d in re.split(r"\n\s*\n", text) if d.strip()]
else:
    docs = [text.strip()] if text.strip() else []
if ss.split and docs:
    st.caption(f"문서 {len(docs)}개로 나눴어요.")

if not docs:
    st.markdown("---")
    st.markdown("👆 글을 넣거나 **예시 불러오기**를 눌러 시작하세요.")
    st.stop()

# ══════════════════════════════════════════════════════════════
# ② 형태소 분석과 빈도표
# ══════════════════════════════════════════════════════════════
step_header(
    "②",
    "형태소 분석과 빈도표",
    "형태소 = 뜻을 가진 가장 작은 말의 단위. 글을 형태소로 쪼갠 뒤, 고른 품사만 골라 몇 번 나왔는지 세요.",
)

pos_set = {code for code, _, _ in POS_OPTIONS if ss[f"pos_{code}"]}
stopwords = set(split_list(ss.stopwords))
user_words = tuple(sorted({w for w in split_list(ss.userwords) if valid_user_word(w)}))
bad_words = [w for w in split_list(ss.userwords) if not valid_user_word(w)]
if bad_words:
    st.sidebar.warning("사용자 사전에 넣지 못한 말: " + ", ".join(bad_words) + " (띄어쓰기 없이 2~20글자)")

# 문서 → 줄 단위로 분석(화면에 줄별로 보여 주기 위해)
doc_lines = [[ln.strip() for ln in d.splitlines() if ln.strip()] for d in docs]
flat_lines = tuple(ln for lines in doc_lines for ln in lines)
try:
    raw_tokens = tokenize_lines(flat_lines, user_words)
except Exception as e:  # 분석기 오류는 화면에 안내
    st.error(f"형태소 분석 중 문제가 생겼어요: {e}")
    st.stop()

# 줄별 결과: (원래 줄, 형태소들, 셀 단어들 [(단어, 품사, 상태)])
line_results = []
doc_words = []  # 문서별로 센 단어 [(단어, 품사)]
stopped = Counter()
pos_iter = iter(raw_tokens)
for lines in doc_lines:
    words_in_doc = []
    for ln in lines:
        toks = next(pos_iter)
        norm = normalize(toks)
        token_state = ["off"] * len(toks)
        for word, pos, idxs in norm:
            if pos not in pos_set:
                continue
            if ss.one_char and len(word) <= 1:
                continue
            state = "stop" if word in stopwords else "on"
            for j in idxs:
                token_state[j] = state
            if state == "stop":
                stopped[word] += 1
            else:
                words_in_doc.append((word, pos))
        line_results.append((ln, toks, token_state, norm))
    doc_words.append(words_in_doc)

base_counter = Counter(wp for d in doc_words for wp in d)
base_df = pd.DataFrame(
    [(w, p, n) for (w, p), n in base_counter.items()], columns=["단어", "품사", "빈도"]
)
ss["_base_words"] = list(base_df["단어"])
table = build_table(base_df)
ss["_shown_table"] = table

# 형태소 분석 결과 보기
with st.expander("🔍 형태소로 쪼갠 결과 보기", expanded=len(flat_lines) <= 12):
    st.markdown(
        '<div class="legend"><span class="chip on">센 단어</span>'
        '<span class="chip stop">불용어로 뺀 단어</span>'
        '<span class="chip">고르지 않은 품사</span></div>',
        unsafe_allow_html=True,
    )
    show_limit = 40
    for ln, toks, states, norm in line_results[:show_limit]:
        chips = "".join(
            f'<span class="chip {"" if s == "off" else s}">{html.escape(f)}<sub>{html.escape(t)}</sub></span>'
            for (f, t, _), s in zip(toks, states)
        )
        counted = [w for w, p, idxs in norm if states[idxs[0]] == "on"]
        st.markdown(f"**{html.escape(ln)}**")
        st.markdown(
            f'<div class="chips">{chips}</div>'
            + (f"→ 센 단어: {html.escape(', '.join(counted))}" if counted else "→ 센 단어 없음"),
            unsafe_allow_html=True,
        )
    if len(line_results) > show_limit:
        st.caption(f"처음 {show_limit}줄만 보여 줘요. (전체 {len(line_results)}줄)")
    st.caption(
        "품사 기호: NNG 일반명사 · NNP 고유명사 · VV 동사 · VA 형용사 · MAG 부사 · SL 외국어 · "
        "J… 조사 · E… 어미 · XSN 명사 접미사 · XSV/XSA 동사·형용사 접미사 · XR 어근 · S… 문장부호"
    )

if table.empty:
    st.warning("고른 품사에 해당하는 단어가 없어요. 사이드바에서 품사를 더 골라 보세요.")
    st.stop()

# 요약
included = table[table["포함"]]
m1, m2, m3 = st.columns(3)
m1.metric("전체 단어 수", f"{int(table['빈도'].sum()):,}")
m2.metric("서로 다른 단어 수", f"{len(table):,}")
m3.metric("제외한 단어 수", f"{int((~table['포함']).sum()):,}")
if stopped:
    st.caption("불용어로 빠진 말: " + ", ".join(f"{w} {n}회" for w, n in stopped.most_common()))

# 버튼 줄
b1, b2, b3, b4, b5, b6 = st.columns([1.1, 0.9, 1.3, 1.1, 1.1, 1.1], vertical_alignment="bottom")
b1.button("✅ 모두 포함", on_click=include_all, width="stretch")
ss.setdefault("top_n_keep", 20)
ss.top_n_keep = max(1, min(int(ss.top_n_keep), len(table)))
b2.number_input("N", min_value=1, max_value=max(1, len(table)), key="top_n_keep")
b3.button("🔝 상위 N개만 포함", on_click=include_top_n, width="stretch")
b4.button("↩️ 편집 되돌리기", on_click=reset_edits, width="stretch", help="고친 이름과 포함 체크를 모두 처음으로")

export = table.copy()
export["포함"] = export["포함"].map({True: "O", False: "X"})
b5.download_button(
    "⬇️ CSV",
    export.to_csv(index=False).encode("utf-8-sig"),  # 엑셀에서 한글이 안 깨지도록 BOM 포함
    file_name="단어빈도.csv",
    mime="text/csv",
    width="stretch",
)
xbuf = io.BytesIO()
with pd.ExcelWriter(xbuf, engine="openpyxl") as xw:
    export.to_excel(xw, sheet_name="빈도표", index=False)
b6.download_button(
    "⬇️ 엑셀",
    xbuf.getvalue(),
    file_name="단어빈도.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    width="stretch",
)

st.caption(
    "✏️ **포함** 체크를 끄면 그래프·워드클라우드에서 바로 빠져요. "
    "**단어** 칸을 고쳐 다른 단어와 같은 이름으로 만들면 빈도가 합쳐져요(예: 좋아요 → 좋다). "
    "열 머리글을 누르면 정렬돼요."
)
editor_key = f"freq_editor_{ss.editor_ver}"
st.data_editor(
    table,
    key=editor_key,
    on_change=on_table_edit,
    args=(editor_key,),
    hide_index=True,
    num_rows="fixed",
    height=min(38 * (len(table) + 1) + 20, 540),
    row_height=38,
    disabled=["품사", "빈도", "상대도수"],
    column_config={
        "포함": st.column_config.CheckboxColumn("포함 ✔", width="small"),
        "단어": st.column_config.TextColumn("단어", help="고쳐 쓰면 같은 이름끼리 빈도가 합쳐져요"),
        "품사": st.column_config.TextColumn("품사"),
        "빈도": st.column_config.NumberColumn("빈도", format="%d"),
        "상대도수": st.column_config.NumberColumn("상대도수", format="%.3f", help="빈도 ÷ 전체 단어 수"),
    },
)
if ss.renames:
    st.caption("고친 이름: " + ", ".join(f"{o} → {n}" for o, n in ss.renames.items()))

# 문서별 단어 목록(이름 고치기·제외 반영)
included_words = list(included["단어"])
inc_set = set(included_words)
final_docs = [[ss.renames.get(w, w) for w, _ in d] for d in doc_words]
final_docs = [[w for w in d if w in inc_set] for d in final_docs]

# ── TF-IDF ────────────────────────────────────────────────────
tfidf_total = None
if ss.split:
    st.markdown("### 📑 TF-IDF 보기")
    st.markdown(
        "- **TF**(단어 빈도): 한 문서 안에서 그 단어가 나온 횟수\n"
        "- **DF**(문서 빈도): 그 단어가 나온 문서의 수\n"
        "- **IDF**: 여러 문서에 두루 나오는 단어일수록 작아지는 값 → **TF·IDF = TF × IDF** 가 크면 '그 문서만의 특징 단어'"
    )
    n_docs = len(docs)
    if n_docs < 2:
        st.info("문서가 1개뿐이에요. 빈 줄로 문서를 2개 이상 나눠야 TF-IDF를 비교할 수 있어요.")
    elif not included_words:
        st.info("포함된 단어가 없어요.")
    else:
        idf_mode = st.radio(
            "IDF 계산 방식",
            ["① 교과서식 n / DF", "② log₁₀(N / DF)"],
            horizontal=True,
            help="n(=N)은 전체 문서 수예요. ②는 모든 문서에 나온 단어의 IDF가 0이 돼요.",
        )
        doc_names = [f"문서{i + 1}" for i in range(n_docs)]
        tf = pd.DataFrame(
            [[Counter(d)[w] for w in included_words] for d in final_docs],
            index=doc_names,
            columns=included_words,
        )
        dfreq = (tf > 0).sum(axis=0)
        if idf_mode.startswith("①"):
            idf = n_docs / dfreq.replace(0, np.nan)
        else:
            idf = np.log10(n_docs / dfreq.replace(0, np.nan))
        tfidf = tf * idf
        tfidf_total = tfidf.sum(axis=0)

        st.markdown(f"**TF 표와 DF·IDF** (문서 수 N = {n_docs})")
        tf_show = pd.concat([tf.astype(float), dfreq.to_frame("DF").T.astype(float), idf.to_frame("IDF").T])

        def shade_summary(row):
            if row.name in ("DF", "IDF"):
                return ["background-color: #FFF6DD; font-weight: 700"] * len(row)
            return [""] * len(row)

        st.dataframe(tf_show.style.format(fmt_num).apply(shade_summary, axis=1), width="stretch")

        st.markdown("**TF·IDF 표** — 문서마다 가장 큰 값을 색칠했어요")

        def highlight_max(row):
            mx = row.max()
            return [
                "background-color: #FFD966; color: #000; font-weight: 800" if (mx > 0 and v == mx) else ""
                for v in row
            ]

        st.dataframe(tfidf.style.format(fmt_num).apply(highlight_max, axis=1), width="stretch")

        tops = []
        for name, row in tfidf.iterrows():
            mx = row.max()
            best = [w for w, v in row.items() if mx > 0 and v == mx]
            tops.append(f"- **{name}**: {', '.join(best) if best else '(없음)'}" + (f" ({fmt_num(mx)})" if best else ""))
        st.markdown("**문서마다 TF·IDF가 가장 큰 단어**\n" + "\n".join(tops))

# ══════════════════════════════════════════════════════════════
# ③ 시각화
# ══════════════════════════════════════════════════════════════
step_header(
    "③",
    "시각화",
    "워드클라우드 = 많이 나온 단어일수록 크게 그린 그림. 막대그래프로 정확한 순위도 함께 확인해요.",
)

if not FONT_OK:
    st.warning("한글 글꼴(fonts/NanumGothic.ttf)이 없어서 그림을 그릴 수 없어요. 위의 안내를 확인해 주세요.")
    st.stop()
if included.empty:
    st.info("포함된 단어가 없어요. 빈도표에서 [모두 포함]을 눌러 보세요.")
    st.stop()

# 막대그래프
st.markdown("### 📊 많이 나온 단어 막대그래프")
max_n = len(included)
if max_n > 1:
    bar_n = st.slider("보여 줄 단어 수 (상위 N개)", 1, min(50, max_n), min(15, max_n))
else:
    bar_n = 1
top = included.head(bar_n)
bar_png = draw_bar_chart(list(top["단어"]), list(top["빈도"]), "빈도")
st.image(bar_png, width=900)
st.download_button("⬇️ 막대그래프 PNG", bar_png, file_name="막대그래프.png", mime="image/png")

# 워드클라우드
st.markdown("### ☁️ 워드클라우드")
oc1, oc2, oc3 = st.columns(3, gap="large")
with oc1:
    size_opts = ["빈도"] + (["TF·IDF"] if tfidf_total is not None else [])
    size_basis = st.radio("크기 기준", size_opts, horizontal=True,
                          help="TF·IDF는 '문서 나누기'를 켰을 때 고를 수 있어요. 문서별 TF·IDF를 더한 값을 써요.")
    max_words = st.slider("최대 단어 수", 10, 200, 100)
    font_range = st.slider("글자 크기 (최소 ~ 최대)", 4, 250, (10, 160))
with oc2:
    cmap_label = st.selectbox("색상 팔레트", list(COLORMAPS))
    single_color = "#2F6DB5"
    if COLORMAPS[cmap_label] is None:
        single_color = st.color_picker("단색 고르기", "#2F6DB5")
    bg_label = st.radio("배경색", list(BACKGROUNDS), horizontal=True)
    shape = st.radio("모양", ["사각형", "원", "하트", "마스크 이미지"], horizontal=True)
    mask_bytes = None
    if shape == "마스크 이미지":
        up = st.file_uploader("마스크 PNG 올리기 (검은 부분에 글자가 채워져요)", type=["png"], key="mask_png")
        if up is not None:
            mask_bytes = up.getvalue()
        else:
            st.caption("PNG를 올리기 전에는 사각형으로 그려요.")
with oc3:
    horizontal = st.slider("가로 단어 비율", 0.0, 1.0, 0.9, 0.05, help="1이면 모두 가로, 0이면 모두 세로")
    rel_scaling = st.slider("크기 차이 강조", 0.0, 1.0, 0.5, 0.05,
                            help="1에 가까울수록 빈도 차이가 글자 크기 차이로 크게 드러나요")
    if st.button("🔀 다시 배치", width="stretch"):
        ss.wc_seed = random.randint(0, 1_000_000)

if size_basis == "TF·IDF":
    freq_pairs = [(w, float(tfidf_total[w])) for w in included_words if tfidf_total[w] > 0]
    if not freq_pairs:
        st.info("TF·IDF가 0보다 큰 단어가 없어요(모든 문서에 나온 단어만 있어요). 크기 기준을 '빈도'로 바꿔 보세요.")
        st.stop()
else:
    freq_pairs = [(w, float(n)) for w, n in zip(included["단어"], included["빈도"])]

opts = (
    ("max_words", max_words),
    ("min_font", font_range[0]),
    ("max_font", max(font_range[1], font_range[0] + 1)),
    ("colormap", COLORMAPS[cmap_label]),
    ("single_color", single_color),
    ("bg", bg_label),
    ("shape", shape if (shape != "마스크 이미지" or mask_bytes) else "사각형"),
    ("horizontal", horizontal),
    ("rel_scaling", rel_scaling),
    ("seed", ss.wc_seed),
)
try:
    wc_png = draw_wordcloud(tuple(freq_pairs), opts, mask_bytes)
except Exception as e:
    st.error(f"워드클라우드를 그리지 못했어요: {e}")
    st.stop()
st.image(wc_png, width="stretch")
st.download_button("⬇️ 워드클라우드 PNG", wc_png, file_name="워드클라우드.png", mime="image/png", type="primary")

st.markdown("---")
st.caption(
    "형태소 분석: Kiwi(kiwipiepy) · 워드클라우드: wordcloud · 글꼴: 나눔고딕(SIL OFL 1.1) · "
    "입력한 글은 서버에 저장하지 않아요."
)
