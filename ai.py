"""구글 Gemini AI 연결. 키가 없거나 오류가 나도 챗봇은 계속 동작해요."""

import streamlit as st

DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """너는 발달장애인을 돕는 다정한 도우미야.
규칙:
- 아주 쉬운 한국어로, 짧은 문장으로 말해. 한 문장은 20자 안팎이야.
- 어려운 단어, 한자어, 영어는 쓰지 마.
- 절대 혼내거나 평가하거나 진단하지 마. 항상 따뜻하고 긍정적으로 말해.
- 대답은 3문장 이하로 해.
- 존댓말(~해요, ~이에요)을 써."""


def _secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default) or default)
    except Exception:
        return default


def is_ready() -> bool:
    key = _secret("GOOGLE_API_KEY")
    return bool(key) and "여기에" not in key


@st.cache_resource
def _client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


def ask(prompt: str) -> str | None:
    """Gemini에게 물어봐요. 실패하면 None 을 돌려줘요."""
    if not is_ready():
        return None
    try:
        from google.genai import types

        response = _client(_secret("GOOGLE_API_KEY")).models.generate_content(
            model=_secret("GEMINI_MODEL", DEFAULT_MODEL),
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.6,
                max_output_tokens=300,
            ),
        )
        text = (response.text or "").strip()
        return text or None
    except Exception:
        return None


def explain_question(question: str) -> str | None:
    return ask(
        f"이 질문을 더 쉽게 설명해 줘. 일상에서 볼 수 있는 짧은 예를 하나 들어 줘.\n질문: {question}"
    )


def praise(kind: str, total: int, max_score: int, diff: int | None) -> str | None:
    """이름은 AI에게 보내지 않아요(개인정보 보호)."""
    extra = ""
    if kind == "사후" and diff is not None:
        if diff > 0:
            extra = f" 사전 평가보다 {diff}점 올랐어."
        elif diff == 0:
            extra = " 사전 평가와 점수가 같아."
    return ask(
        f"{kind} 평가를 끝까지 한 사람에게 칭찬과 응원의 말을 해 줘. "
        f"점수는 {max_score}점 중 {total}점이야.{extra} "
        "점수가 낮아도 절대 실망시키지 말고, 끝까지 한 것을 크게 칭찬해 줘."
    )
