
import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# ==========================================
# 기본 설정
# ==========================================
st.set_page_config(
    page_title="팔각도와 부상기간, 부상 일수",
    page_icon="⚾",
    layout="wide"
)

st.title("⚾ 팔각도와 부상기간, 부상 일수")
st.markdown(
    "선수들의 팔 각도와 부상 횟수 및 부상 일수 사이의 관계를 산점도로 확인합니다."
)

# ==========================================
# GitHub 데이터 주소
# ==========================================
# 아래 주소를 본인의 GitHub 저장소에 올린 CSV의
# Raw 주소로 변경하세요.

GITHUB_CSV_URL = "https://docs.google.com/spreadsheets/d/1I0jc_dkPFAqInxhxaKKccfLjQ8na9TKx/edit?gid=1503298569#gid=1503298569"


# ==========================================
# 데이터 불러오기
# ==========================================
@st.cache_data(ttl=600)
def load_data(url):
    return pd.read_csv(url, encoding="utf-8-sig")


try:
    if "본인아이디" in GITHUB_CSV_URL:
        st.error("main.py에서 GitHub Raw 주소를 먼저 설정해 주세요.")
        st.stop()

    data = load_data(GITHUB_CSV_URL)

except Exception as e:
    st.error("GitHub 데이터를 불러오지 못했습니다.")
    st.error(f"오류 내용: {e}")
    st.info("GitHub CSV 파일의 Raw 주소와 공개 설정을 확인해 주세요.")
    st.stop()


if data.empty:
    st.error("데이터가 비어 있습니다.")
    st.stop()

# ==========================================
# 데이터 확인
# ==========================================
st.subheader("📋 원본 데이터")

st.write(f"전체 데이터: **{len(data):,}행**")

with st.expander("원본 데이터 펼쳐 보기"):
    st.dataframe(data, use_container_width=True)

# ==========================================
# 데이터 열 선택
# ==========================================
st.divider()
st.subheader("🔧 분석에 사용할 열 선택")

columns = list(data.columns)

col1, col2 = st.columns(2)

with col1:
    player_col = st.selectbox(
        "선수 이름 열",
        columns
    )

    angle_col = st.selectbox(
        "팔 각도 열",
        columns
    )

with col2:
    duration_col = st.selectbox(
        "부상 일수 열",
        columns
    )

    count_mode = st.radio(
        "부상 횟수 계산 방법",
        [
            "부상 기록의 행 개수로 계산",
            "부상 횟수 열의 값 사용"
        ]
    )

    if count_mode == "부상 횟수 열의 값 사용":
        count_col = st.selectbox(
            "부상 횟수 열",
            columns
        )
    else:
        count_col = None

# ==========================================
# 집계 방식
# ==========================================
st.divider()
st.subheader("📊 선수별 데이터 처리")

aggregation_mode = st.radio(
    "데이터 형태를 선택하세요.",
    [
        "선수별 요약 데이터",
        "부상 기록별 데이터"
    ],
    help=(
        "선수별 요약 데이터: 한 선수의 정보가 이미 한 행에 정리된 경우\n"
        "부상 기록별 데이터: 한 선수가 부상할 때마다 별도 행으로 기록된 경우"
    )
)

# ==========================================
# 숫자 변환
# ==========================================
def numeric(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("도", "", regex=False)
        .str.replace("일", "", regex=False)
        .str.strip(),
        errors="coerce"
    )


df = pd.DataFrame()

df["선수"] = data[player_col].astype(str).str.strip()
df["팔 각도"] = numeric(data[angle_col])
df["부상 일수"] = numeric(data[duration_col])

if count_col is not None:
    df["부상 횟수"] = numeric(data[count_col])
else:
    df["부상 횟수"] = 1

# 이름이 없는 행 제거
df = df[
    df["선수"].notna()
    & (df["선수"] != "")
    & (df["선수"].str.lower() != "nan")
]

# 팔 각도는 0~180도 범위만 허용
invalid_angle = (
    df["팔 각도"].notna()
    & ((df["팔 각도"] < 0) | (df["팔 각도"] > 180))
)

invalid_angle_count = int(invalid_angle.sum())

# 팔 각도가 없는 데이터 또는 범위를 벗어난 데이터 제외
df = df[
    df["팔 각도"].between(0, 180)
].copy()

# ==========================================
# 선수별 집계
# ==========================================
if aggregation_mode == "부상 기록별 데이터":

    if count_col is None:
        # 한 행을 부상 1회로 계산
        df["부상 횟수"] = 1

    # 같은 선수의 팔 각도는 평균으로 집계
    # 부상 횟수와 부상 일수는 합계로 집계
    result = df.groupby("선수").agg(
        팔각도=("팔 각도", "mean"),
        부상횟수=("부상 횟수", "sum"),
        부상일수=("부상 일수", "sum")
    ).reset_index()

else:

    # 이미 선수별로 정리된 데이터
    # 중복 선수가 있다면 각도는 평균, 횟수와 일수는 합계
    result = df.groupby("선수").agg(
        팔각도=("팔 각도", "mean"),
        부상횟수=("부상 횟수", "sum"),
        부상일수=("부상 일수", "sum")
    ).reset_index()

# 부상 횟수와 부상 일수가 모두 유효한 데이터
result["부상횟수"] = result["부상횟수"].fillna(0)
result["부상일수"] = result["부상일수"].fillna(0)

result = result[
    (result["부상횟수"] >= 0)
    & (result["부상일수"] >= 0)
].copy()

if len(result) < 2:
    st.error("분석 가능한 선수가 2명 미만입니다.")
    st.stop()

# ==========================================
# 데이터 검증
# ==========================================
st.divider()
st.subheader("🔍 데이터 검증 결과")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("분석 선수 수", f"{len(result):,}명")

with c2:
    st.metric(
        "팔 각도 최솟값",
        f"{result['팔각도'].min():.1f}°"
    )

with c3:
    st.metric(
        "팔 각도 최댓값",
        f"{result['팔각도'].max():.1f}°"
    )

if invalid_angle_count > 0:
    st.warning(
        f"팔 각도가 0~180도 범위를 벗어난 원본 기록 "
        f"{invalid_angle_count}개를 제외했습니다. "
        "원본 열을 다시 확인해 주세요."
    )

if result["팔각도"].nunique() < 2:
    st.warning("팔 각도가 모두 같아 산점도에서 관계를 비교하기 어렵습니다.")

# ==========================================
# 첫 번째 그래프
# ==========================================
st.divider()

st.header("1️⃣ 팔 각도와 부상 횟수")

st.markdown(
    """
    - X축: 선수의 팔 각도
    - Y축: 선수의 부상 횟수
    - 점 하나: 선수 한 명
    """
)

fig1 = px.scatter(
    result,
    x="팔각도",
    y="부상횟수",
    hover_name="선수",
    hover_data={
        "팔각도": ":.1f",
        "부상횟수": True,
        "부상일수": True
    },
    labels={
        "팔각도": "팔 각도 (°)",
        "부상횟수": "부상 횟수 (회)"
    },
    title="선수별 팔 각도와 부상 횟수",
)

fig1.update_traces(
    marker=dict(
        size=11,
        opacity=0.75
    )
)

fig1.update_layout(
    height=550,
    xaxis=dict(rangemode="tozero"),
    yaxis=dict(rangemode="tozero")
)

st.plotly_chart(fig1, use_container_width=True)

# ==========================================
# 두 번째 그래프
# ==========================================
st.divider()

st.header("2️⃣ 팔 각도와 부상 일수")

st.markdown(
    """
    - X축: 선수의 팔 각도
    - Y축: 선수의 부상 일수
    - 점 하나: 선수 한 명
    """
)

fig2 = px.scatter(
    result,
    x="팔각도",
    y="부상일수",
    hover_name="선수",
    hover_data={
        "팔각도": ":.1f",
        "부상횟수": True,
        "부상일수": True
    },
    labels={
        "팔각도": "팔 각도 (°)",
        "부상일수": "부상 일수 (일)"
    },
    title="선수별 팔 각도와 부상 일수",
)

fig2.update_traces(
    marker=dict(
        size=11,
        opacity=0.75
    )
)

fig2.update_layout(
    height=550,
    xaxis=dict(rangemode="tozero"),
    yaxis=dict(rangemode="tozero")
)

st.plotly_chart(fig2, use_container_width=True)

# ==========================================
# 선수별 데이터 표
# ==========================================
st.divider()

st.header("📑 선수별 분석 데이터")

st.dataframe(
    result.rename(columns={
        "팔각도": "팔 각도 (°)",
        "부상횟수": "부상 횟수 (회)",
        "부상일수": "부상 일수 (일)"
    }).sort_values("팔 각도 (°)"),
    use_container_width=True,
    hide_index=True
)

# ==========================================
# 데이터 다운로드
# ==========================================
csv = result.to_csv(
    index=False,
    encoding="utf-8-sig"
)

st.download_button(
    "📥 선수별 분석 데이터 다운로드",
    data=csv,
    file_name="팔각도_부상분석.csv",
    mime="text/csv"
)

# ==========================================
# 마무리
# ==========================================
st.divider()

st.subheader("💡 그래프 해석")

st.markdown(
    """
    두 산점도에서 점들이 어떤 형태로 분포하는지 관찰해 보세요.

    - 오른쪽으로 갈수록 점들이 위쪽에 모이는가?
    - 오른쪽으로 갈수록 점들이 아래쪽에 모이는가?
    - 특정한 방향 없이 흩어져 있는가?

    이를 통해 팔 각도와 부상 횟수 및 부상 일수 사이에
    어떤 관계가 나타나는지 탐구할 수 있습니다.
    """
)

st.warning(
    "산점도에서 나타나는 관계만으로 팔 각도가 부상의 원인이라고 "
    "단정할 수는 없습니다."
)
