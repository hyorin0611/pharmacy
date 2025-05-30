import streamlit as st
import google.generativeai as genai

# --- secrets.toml에서 Gemini API 키 불러오기 ---
# Streamlit Cloud 배포 시, secrets는 Settings > Secrets에서 환경변수로 등록해야 합니다.
gemini_api_key = st.secrets.get("GOOGLE_API_KEY", "")
if not gemini_api_key:
    st.error("Gemini API 키가 설정되어 있지 않습니다. .streamlit/secrets.toml 또는 Streamlit Cloud Secrets를 확인하세요.")
    st.stop()
genai.configure(api_key=gemini_api_key)

# --- 페이지 설정 및 타이틀 ---
st.set_page_config(page_title="약대생 Q&A 챗봇 💊", layout="centered")
st.title("약대생 Q&A 챗봇 💊")
st.caption("Gemini 1.5-flash 기반, 약학 전공 Q&A 및 퀴즈 챗봇")

# --- 과목 리스트 및 세션 상태 초기화 ---
subjects = ["자동 분류", "약물학", "약물치료학", "생화학", "해부생리학", "미생물학", "유기화학"]
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_subject" not in st.session_state:
    st.session_state.last_subject = "자동 분류"
if "last_question" not in st.session_state:
    st.session_state.last_question = ""
if "last_answer" not in st.session_state:
    st.session_state.last_answer = ""

# --- 사이드바 ---
st.sidebar.header("사용법 안내")
st.sidebar.markdown("""
- 과목을 선택하거나 '자동 분류'로 질문을 입력하세요.
- 답변에는 교과서 스타일 설명, 퀴즈, 시험 대비 요약이 포함됩니다.
- '다시 설명해줘', '예시 더 보기' 버튼으로 대화를 확장할 수 있습니다.
""")

# --- 메인 UI ---
st.subheader("1️⃣ 과목 선택 및 질문 입력")
subject = st.selectbox(
    "과목을 선택하세요",
    subjects,
    index=subjects.index(st.session_state.last_subject) if st.session_state.last_subject in subjects else 0,
    help="'자동 분류'를 선택하면 Gemini가 질문을 분석해 과목을 분류합니다."
)
question = st.text_area("질문을 입력하세요 (최소 5자)", value=st.session_state.last_question, height=80)
col1, col2 = st.columns([1,1])
with col1:
    submit = st.button("질문 제출", use_container_width=True)
with col2:
    reset = st.button("입력 초기화", use_container_width=True)

# --- 과목 자동 분류 프롬프트 ---
subject_classify_prompt = (
    "아래 질문이 어떤 약학 과목(약물학, 약물치료학, 생화학, 해부생리학, 미생물학, 유기화학)에 가장 적합한지 한 단어로만 답해줘.\n"
    "질문: "
)

def classify_subject(question):
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(subject_classify_prompt + question)
    return response.text.strip()

def build_gemini_prompt(question, subject):
    return f"""
[교과서 스타일 설명]
- 정의 → 기전 → 임상 → 예시 순서로 설명해줘.

[3~5지선다형 퀴즈]
- 질문 내용과 관련된 3~5지선다형 퀴즈 1개를 내고, 사용자가 선택하면 즉시 피드백(정답/해설)을 제공해줘.

[시험 대비 요약]
- 시험 대비용 슬라이드 형식으로 핵심 요약을 제공해줘.

과목: {subject}
질문: {question}
"""

# --- 질문 제출 처리 ---
if submit:
    if not question.strip() or len(question.strip()) < 5:
        st.warning("질문을 5자 이상 입력해 주세요.")
    else:
        # 자동 분류
        selected_subject = subject
        if subject == "자동 분류":
            with st.spinner("질문을 분석하여 과목을 분류 중입니다..."):
                selected_subject = classify_subject(question)
                if selected_subject not in subjects[1:]:
                    st.warning(f"과목 자동 분류에 실패했습니다. 수동으로 선택해 주세요. (결과: {selected_subject})")
                    selected_subject = "자동 분류"
        st.session_state.last_subject = selected_subject
        st.session_state.last_question = question
        with st.spinner("Gemini가 답변을 생성 중입니다..."):
            try:
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = build_gemini_prompt(question, selected_subject)
                response = model.generate_content(prompt)
                answer = response.text if hasattr(response, "text") else str(response)
                st.session_state.last_answer = answer
                st.session_state.chat_history.append(("user", question, selected_subject))
                st.session_state.chat_history.append(("ai", answer, selected_subject))
                st.success("답변:")
                st.write(answer)
            except Exception as e:
                st.error(f"API 호출 중 오류가 발생했습니다: {e}")

if reset:
    st.session_state.last_question = ""
    st.experimental_rerun()

# --- 대화 확장 버튼 ---
if st.session_state.last_answer:
    st.divider()
    st.subheader("2️⃣ 대화 확장")
    col3, col4 = st.columns([1,1])
    with col3:
        if st.button("다시 설명해줘"):
            st.session_state.last_question = st.session_state.last_question + "\n다시 설명해줘. 더 쉽게!"
            st.experimental_rerun()
    with col4:
        if st.button("예시 더 보기"):
            st.session_state.last_question = st.session_state.last_question + "\n예시를 더 많이 보여줘."
            st.experimental_rerun()

# --- 이전 대화 출력 ---
st.divider()
st.subheader("3️⃣ 이전 대화 보기")
with st.expander("🗂️ 이전 대화 보기"):
    for role, msg, subj in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(f"**[{subj}]** {msg}")
