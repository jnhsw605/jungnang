"""발달장애인을 위한 쉬운 사전·사후 평가 챗봇 (Streamlit)"""

import csv
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import ai
from questions import ANSWERS, QUESTIONS

RESULT_FILE = Path(__file__).parent / "results.csv"
TOTAL = len(QUESTIONS)
MAX_SCORE = TOTAL * max(a[2] for a in ANSWERS)

st.set_page_config(page_title="쉬운 평가 도우미", page_icon="🌼", layout="centered")

# 큰 글씨, 큰 버튼
st.markdown(
    """
    <style>
    html, body, [class*="css"] { font-size: 24px; }
    .bubble {
        background: #FFF3D6; border-radius: 24px; padding: 28px;
        font-size: 34px; font-weight: 700; line-height: 1.5;
        text-align: center; margin: 12px 0 24px 0;
    }
    .big-emoji { font-size: 90px; text-align: center; }
    .stButton > button {
        width: 100%; min-height: 84px; font-size: 28px; font-weight: 700;
        border-radius: 20px; border: 3px solid #2E7D32;
    }
    .stTextInput input { font-size: 28px; height: 64px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def speak(text: str, label: str = "🔊 소리로 듣기") -> None:
    """브라우저의 읽어주기 기능으로 글을 소리로 읽어줘요."""
    # AI가 쓴 글이 <script>를 깨뜨리지 못하게 '<' 를 바꿔 줘요.
    safe = json.dumps(text).replace("<", "\\u003c")
    html = f"""
        <button onclick="say()" style="font-size:26px;padding:14px 28px;
            border-radius:16px;border:3px solid #1565C0;background:#E3F2FD;
            cursor:pointer;font-weight:700;">{label}</button>
        <script>
        function say() {{
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance({safe});
            u.lang = 'ko-KR'; u.rate = 0.85;
            window.speechSynthesis.speak(u);
        }}
        </script>
        """
    if hasattr(st, "iframe"):
        st.iframe(html, height=80)
    else:
        components.html(html, height=80)


def init_state() -> None:
    defaults = {
        "stage": "start", "name": "", "kind": "사전", "index": 0,
        "scores": [], "explain": {}, "praise": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def save_result() -> None:
    new_file = not RESULT_FILE.exists()
    with RESULT_FILE.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(
                ["날짜", "이름", "구분", "총점", "만점"]
                + [f"문항{i + 1}" for i in range(TOTAL)]
            )
        writer.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                st.session_state.name,
                st.session_state.kind,
                sum(st.session_state.scores),
                MAX_SCORE,
                *st.session_state.scores,
            ]
        )


def previous_total(name: str, kind: str):
    """같은 사람의 가장 최근 '다른 구분'(사전↔사후) 점수를 찾아요."""
    if not RESULT_FILE.exists():
        return None
    other = "사전" if kind == "사후" else "사후"
    found = None
    with RESULT_FILE.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["이름"] == name and row["구분"] == other:
                found = int(row["총점"])
    return found


def restart() -> None:
    for key in ("stage", "name", "kind", "index", "scores", "explain", "praise"):
        st.session_state.pop(key, None)


def screen_start() -> None:
    st.markdown('<div class="big-emoji">🌼</div>', unsafe_allow_html=True)
    st.markdown('<div class="bubble">안녕하세요!<br>같이 해봐요.</div>', unsafe_allow_html=True)

    st.session_state.name = st.text_input("이름을 써 주세요", value=st.session_state.name)
    st.write("무엇을 할까요?")
    col1, col2 = st.columns(2)
    start = None
    if col1.button("📘 사전 평가\n(배우기 전)"):
        start = "사전"
    if col2.button("📗 사후 평가\n(배운 후)"):
        start = "사후"

    if start:
        if not st.session_state.name.strip():
            st.warning("이름을 먼저 써 주세요.")
            return
        st.session_state.kind = start
        st.session_state.stage = "quiz"
        st.session_state.index = 0
        st.session_state.scores = []
        st.session_state.explain = {}
        st.session_state.praise = None
        st.rerun()


def screen_quiz() -> None:
    i = st.session_state.index
    text, emoji = QUESTIONS[i]

    st.progress(i / TOTAL, text=f"{i + 1}번 / 전체 {TOTAL}개")
    st.markdown(f'<div class="big-emoji">{emoji}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="bubble">{text}</div>', unsafe_allow_html=True)
    speak(text)

    if ai.is_ready():
        if i not in st.session_state.explain:
            if st.button("🤔 쉽게 설명해 주세요", key=f"explain-{i}"):
                with st.spinner("생각하고 있어요..."):
                    answer = ai.explain_question(text)
                st.session_state.explain[i] = answer or "지금은 AI가 쉬고 있어요. 선생님께 물어보세요."
                st.rerun()
        else:
            st.info(st.session_state.explain[i])
            speak(st.session_state.explain[i], "🔊 설명 듣기")

    for label, face, score in ANSWERS:
        if st.button(f"{face}  {label}", key=f"ans-{i}-{score}"):
            st.session_state.scores.append(score)
            if i + 1 >= TOTAL:
                save_result()
                st.session_state.stage = "done"
            else:
                st.session_state.index += 1
            st.rerun()

    if i > 0 and st.button("⬅️ 이전 질문으로"):
        st.session_state.scores.pop()
        st.session_state.index -= 1
        st.rerun()


def screen_done() -> None:
    total = sum(st.session_state.scores)
    st.balloons()
    st.markdown('<div class="big-emoji">🎉</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="bubble">{st.session_state.name}님,<br>끝까지 했어요!<br>정말 잘했어요!</div>',
        unsafe_allow_html=True,
    )
    speak(f"{st.session_state.name}님, 끝까지 했어요! 정말 잘했어요!")

    st.write(f"내 점수: **{total}점** (만점 {MAX_SCORE}점)")

    before = previous_total(st.session_state.name, st.session_state.kind)
    if before is not None:
        other = "사전" if st.session_state.kind == "사후" else "사후"
        st.write(f"{other} 점수: **{before}점**")
        if st.session_state.kind == "사후":
            diff = total - before
            if diff > 0:
                st.success(f"👏 {diff}점 올랐어요!")
            elif diff == 0:
                st.info("😊 점수가 같아요. 잘 유지했어요!")
            else:
                st.info("😊 괜찮아요. 다음에 또 해봐요!")

    if ai.is_ready():
        if st.session_state.praise is None:
            diff = total - before if before is not None else None
            with st.spinner("응원의 말을 쓰고 있어요..."):
                st.session_state.praise = (
                    ai.praise(st.session_state.kind, total, MAX_SCORE, diff) or ""
                )
        if st.session_state.praise:
            st.success(st.session_state.praise)
            speak(st.session_state.praise, "🔊 응원 듣기")

    if st.button("🏠 처음으로"):
        restart()
        st.rerun()


init_state()
{"start": screen_start, "quiz": screen_quiz, "done": screen_done}[st.session_state.stage]()
