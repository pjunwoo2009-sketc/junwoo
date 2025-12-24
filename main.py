import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ===============================
# 기본 설정
# ===============================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 (Streamlit)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# 유틸: 한글 파일명 정규화
# ===============================
def normalize_name(name):
    return unicodedata.normalize("NFC", name)

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data(data_dir: Path):
    env_data = {}
    for f in data_dir.iterdir():
        if f.suffix.lower() == ".csv":
            school = normalize_name(f.stem.split("_")[0])
            df = pd.read_csv(f)
            df["time"] = pd.to_datetime(df["time"])
            env_data[school] = df
    return env_data

@st.cache_data
def load_growth_data(data_dir: Path):
    xlsx_file = None
    for f in data_dir.iterdir():
        if f.suffix.lower() == ".xlsx":
            xlsx_file = f
            break

    if xlsx_file is None:
        return {}

    growth = {}
    xls = pd.ExcelFile(xlsx_file)
    for sheet in xls.sheet_names:
        school = normalize_name(sheet)
        df = pd.read_excel(xlsx_file, sheet_name=sheet)
        df["학교"] = school
        growth[school] = df
    return growth

# ===============================
# 데이터 로드
# ===============================
DATA_DIR = Path("data")

with st.spinner("📂 데이터 로딩 중..."):
    if not DATA_DIR.exists():
        st.error("❌ data 폴더를 찾을 수 없습니다.")
        st.stop()

    env_data = load_environment_data(DATA_DIR)
    growth_data = load_growth_data(DATA_DIR)

    if not env_data or not growth_data:
        st.error("❌ 데이터 파일이 없거나 비어 있습니다.")
        st.stop()

# ===============================
# 공통 학교 추출 (🔥 핵심 수정)
# ===============================
common_schools = sorted(set(env_data.keys()) & set(growth_data.keys()))

if len(common_schools) == 0:
    st.error("❌ 환경 데이터와 생육 데이터가 일치하는 학교가 없습니다.")
    st.stop()

missing_env = set(growth_data.keys()) - set(env_data.keys())
if missing_env:
    st.warning(f"⚠ 환경 데이터가 없는 학교: {', '.join(missing_env)}")

# ===============================
# 사이드바
# ===============================
schools = ["전체"] + common_schools
selected_school = st.sidebar.selectbox("🏫 학교 선택", schools)

# ===============================
# 제목 & 탭
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ===============================
# Tab 1: 실험 개요
# ===============================
with tab1:
    st.subheader("🔍 연구 배경 및 목적")
    st.markdown("""
    본 연구는 **극지 환경을 모사한 조건**에서  
    **EC(전기전도도) 농도 차이가 식물 생육에 미치는 영향**을 분석하여  
    **최적 EC 농도 조건**을 도출하는 것을 목표로 한다.
    """)

    summary = []
    total_plants = 0

    for school in common_schools:
        df = growth_data[school]
        cnt = len(df)
        total_plants += cnt

        summary.append({
            "학교명": school,
            "EC 목표": round(env_data[school]["ec"].mean(), 2),
            "개체수": cnt
        })

    summary_df = pd.DataFrame(summary)
    st.dataframe(summary_df, use_container_width=True)

    avg_temp = pd.concat(env_data[s]["temperature"] for s in common_schools).mean()
    avg_hum = pd.concat(env_data[s]["humidity"] for s in common_schools).mean()

    growth_all = pd.concat(growth_data[s] for s in common_schools)
    ec_map = {s: env_data[s]["ec"].mean() for s in common_schools}
    growth_all["EC"] = growth_all["학교"].map(ec_map)

    optimal_ec = growth_all.groupby("EC")["생중량(g)"].mean().idxmax()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total_plants)
    c2.metric("평균 온도(℃)", f"{avg_temp:.1f}")
    c3.metric("평균 습도(%)", f"{avg_hum:.1f}")
    c4.metric("최적 EC", f"{optimal_ec:.2f}", delta="⭐")

# ===============================
# Tab 2: 환경 데이터
# ===============================
with tab2:
    st.subheader("📊 학교별 환경 평균 비교")

    avg_env = []
    for s in common_schools:
        df = env_data[s]
        avg_env.append({
            "학교": s,
            "온도": df["temperature"].mean(),
            "습도": df["humidity"].mean(),
            "pH": df["ph"].mean(),
            "EC": df["ec"].mean()
        })

    avg_df = pd.DataFrame(avg_env)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "평균 EC")
    )
    fig.add_bar(x=avg_df["학교"], y=avg_df["온도"], row=1, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["습도"], row=1, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["pH"], row=2, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["EC"], row=2, col=2)

    fig.update_layout(
        height=600,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    if selected_school != "전체":
        df = env_data[selected_school]
        fig_ts = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig_ts.add_line(x=df["time"], y=df["temperature"], row=1, col=1)
        fig_ts.add_line(x=df["time"], y=df["humidity"], row=2, col=1)
        fig_ts.add_line(x=df["time"], y=df["ec"], row=3, col=1)

        fig_ts.update_layout(
            height=700,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("📥 환경 데이터 원본"):
        all_env = pd.concat(env_data[s] for s in common_schools)
        st.dataframe(all_env, use_container_width=True)

        buffer = io.BytesIO()
        all_env.to_csv(buffer, index=False)
        buffer.seek(0)
        st.download_button(
            "CSV 다운로드",
            data=buffer,
            file_name="환경데이터_전체.csv",
            mime="text/csv"
        )

# ===============================
# Tab 3: 생육 결과
# ===============================
with tab3:
    st.subheader("🥇 EC별 평균 생중량")

    ec_avg = growth_all.groupby("EC")["생중량(g)"].mean().reset_index()
    fig_ec = px.bar(ec_avg, x="EC", y="생중량(g)", text_auto=".2f")
    fig_ec.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig_ec, use_container_width=True)

    st.subheader("📦 학교별 생중량 분포")
    fig_box = px.box(growth_all, x="학교", y="생중량(g)")
    fig_box.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("📈 상관관계 분석")
    c1, c2 = st.columns(2)

    with c1:
        fig1 = px.scatter(
            growth_all,
            x="잎 수(장)",
            y="생중량(g)"
        )
        fig1.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        fig2 = px.scatter(
            growth_all,
            x="지상부 길이(mm)",
            y="생중량(g)"
        )
        fig2.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig2, use_container_width=True)

    with st.expander("📥 생육 데이터 원본"):
        st.dataframe(growth_all, use_container_width=True)

        buffer = io.BytesIO()
        growth_all.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
