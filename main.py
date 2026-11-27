
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import BytesIO

# --------------------------------------------------
# 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="팔각도와 부상기간, 부상 일수",
    page_icon="⚾",
    layout="wide"
)

st.title("⚾ 팔각도와 부상기간, 부상 일수")
st.markdown(
    "선수의 팔 각도와 부상 횟수 및 부상 기간 사이의 관계를 분석합니다."
)

SHEET_ID = "1I0jc_dkPFAqInxhxaKKccfLjQ8na9TKx"
CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export"
    "?format=csv&gid=0"
)

# --------------------------------------------------
# 데이터 불러오기
# --------------------------------------------------
@st.cache_data(ttl=600)
def load_google_sheet():
    response = requests.get(CSV_URL, timeout=20)
    response.raise_for_status()

    return pd.read_csv(BytesIO(response.content))


def load_uploaded_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)

    return pd.read_excel(file)


# --------------------------------------------------
# 열 이름 자동 인식
# --------------------------------------------------
def find_column(columns, keywords):
    for col in columns:
        name = str(col).replace(" ", "").lower()

        for keyword in keywords:
            if keyword.replace(" ", "").lower() in name:
                return col

    return None


def to_numeric(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("도", "", regex=False)
        .str.replace("일", "", regex=False)
        .str.strip(),
        errors="coerce"
    )


# --------------------------------------------------
# 데이터 선택
# --------------------------------------------------
st.sidebar.header("📂 데이터 설정")

uploaded_file = st.sidebar.file_uploader(
    "CSV 또는 엑셀 파일 업로드",
    type=["csv", "xlsx", "xls"]
)

data = None

if uploaded_file is not None:
    try:
        data = load_uploaded_file(uploaded_file)
        st.sidebar.success("업로드한 파일을 불러왔습니다.")

    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
        st.stop()

else:
    try:
        data = load_google_sheet()
        st.sidebar.success("구글 스프레드시트를 불러왔습니다.")

    except Exception:
        st.warning(
            "구글 스프레드시트에 접근할 수 없습니다. "
            "공유 권한을 확인하거나 CSV/엑셀 파일을 업로드해 주세요."
        )
        st.info(
            "구글 스프레드시트의 공유 설정에서 링크가 있는 사용자가 "
            "볼 수 있도록 설정해야 합니다."
        )
        st.stop()


if data is None or data.empty:
    st.error("분석할 데이터가 없습니다.")
    st.stop()


# --------------------------------------------------
# 데이터 기본 정보
# --------------------------------------------------
st.subheader("📋 데이터 확인")

col1, col2 = st.columns(2)

with col1:
    st.metric("전체 데이터 수", f"{len(data):,}개")

with col2:
    st.metric("전체 열 개수", f"{len(data.columns):,}개")

with st.expander("원본 데이터 확인"):
    st.dataframe(data, use_container_width=True)


# --------------------------------------------------
# 분석에 사용할 열 선택
# --------------------------------------------------
st.subheader("🔧 분석에 사용할 데이터 선택")

columns = list(data.columns)

player_guess = find_column(
    columns,
    ["선수명", "선수", "이름", "player", "name"]
)

angle_guess = find_column(
    columns,
    ["팔각도", "팔 각도", "arm angle", "angle"]
)

count_guess = find_column(
    columns,
    ["부상횟수", "부상 횟수", "부상건수", "injury count",
     "injuries", "count"]
)

duration_guess = find_column(
    columns,
    ["부상기간", "부상 기간", "부상일수", "부상 일수",
     "injury duration", "days injured", "duration", "days"]
)


def default_index(options, guess):
    if guess in options:
        return options.index(guess)
    return 0


with st.container(border=True):
    st.markdown("**데이터 열 지정**")

    player_options = ["선수 이름 사용 안 함"] + columns

    player_choice = st.selectbox(
        "선수 이름 열",
        player_options,
        index=(
            player_options.index(player_guess)
            if player_guess in player_options else 0
        )
    )

    angle_col = st.selectbox(
        "선수의 팔 각도 열 (X축)",
        columns,
        index=default_index(columns, angle_guess)
    )

    count_col = st.selectbox(
        "부상 횟수 열 (첫 번째 그래프 Y축)",
        columns,
        index=default_index(columns, count_guess)
    )

    duration_col = st.selectbox(
        "부상 기간 또는 부상 일수 열 (두 번째 그래프 Y축)",
        columns,
        index=default_index(columns, duration_guess)
    )


player_col = (
    None if player_choice == "선수 이름 사용 안 함"
    else player_choice
)


# --------------------------------------------------
# 데이터 전처리
# --------------------------------------------------
df = data.copy()

df["_팔각도"] = to_numeric(df[angle_col])
df["_부상횟수"] = to_numeric(df[count_col])
df["_부상기간"] = to_numeric(df[duration_col])

if player_col:
    df["_선수명"] = df[player_col].astype(str)
else:
    df["_선수명"] = [
        f"선수 {i+1}" for i in range(len(df))
    ]

# 분석에 필요한 값이 모두 있는 행만 사용
analysis_df = df.dropna(
    subset=["_팔각도", "_부상횟수", "_부상기간"]
).copy()

# 음수 데이터 제거
analysis_df = analysis_df[
    (analysis_df["_팔각도"] >= 0)
    & (analysis_df["_부상횟수"] >= 0)
    & (analysis_df["_부상기간"] >= 0)
]

if len(analysis_df) < 2:
    st.error(
        "분석 가능한 데이터가 부족합니다. "
        "열 선택과 원본 데이터를 확인해 주세요."
    )
    st.stop()


st.divider()

st.subheader("📊 분석 데이터 요약")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("분석에 사용된 데이터", f"{len(analysis_df):,}개")

with c2:
    st.metric(
        "평균 팔 각도",
        f"{analysis_df['_팔각도'].mean():.2f}°"
    )

with c3:
    st.metric(
        "평균 부상 횟수",
        f"{analysis_df['_부상횟수'].mean():.2f}회"
    )


# --------------------------------------------------
# 회귀분석 함수
# --------------------------------------------------
def draw_regression_graph(df, x_col, y_col, title, x_title, y_title):

    x = df[x_col].to_numpy(dtype=float)
    y = df[y_col].to_numpy(dtype=float)

    fig = go.Figure()

    # 선수별 산점도
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            name="선수 데이터",
            text=df["_선수명"],
            customdata=np.column_stack((x, y)),
            hovertemplate=(
                "선수: %{text}<br>"
                "팔 각도: %{x:.2f}°<br>"
                + y_title + ": %{y:.2f}"
                + "<extra></extra>"
            ),
            marker=dict(
                size=10,
                opacity=0.75
            )
        )
    )

    regression_text = "회귀분석 불가"
    r_squared = None

    # 서로 다른 X값이 2개 이상일 때 회귀분석
    if len(np.unique(x)) >= 2:

        slope, intercept = np.polyfit(x, y, 1)

        predicted = slope * x + intercept

        ss_res = np.sum((y - predicted) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        if ss_tot != 0:
            r_squared = 1 - ss_res / ss_tot

        line_x = np.linspace(x.min(), x.max(), 100)
        line_y = slope * line_x + intercept

        fig.add_trace(
            go.Scatter(
                x=line_x,
                y=line_y,
                mode="lines",
                name="선형 회귀선",
                line=dict(
                    width=3,
                    dash="dash"
                )
            )
        )

        regression_text = (
            f"회귀식: y = {slope:.4f}x "
            f"{intercept:+.4f}"
        )

    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=550,
        hovermode="closest",
        legend=dict(
            orientation="h",
            y=1.1
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"**{regression_text}**")

    if r_squared is not None:
        st.metric(
            "결정계수 (R²)",
            f"{r_squared:.4f}"
        )

    return r_squared


# --------------------------------------------------
# 첫 번째 그래프
# --------------------------------------------------
st.header("1️⃣ 팔 각도와 부상 횟수의 관계")

st.markdown(
    """
    선수의 팔 각도를 X축에, 부상 횟수를 Y축에 나타낸 산점도입니다.

    각 점은 한 선수의 데이터를 의미하며,
    점선은 두 변수 사이의 선형 회귀선을 나타냅니다.
    """
)

r2_count = draw_regression_graph(
    analysis_df,
    "_팔각도",
    "_부상횟수",
    "팔 각도와 부상 횟수의 관계",
    "팔 각도 (°)",
    "부상 횟수 (회)"
)


# --------------------------------------------------
# 두 번째 그래프
# --------------------------------------------------
st.divider()

st.header("2️⃣ 팔 각도와 부상 기간의 관계")

st.markdown(
    """
    선수의 팔 각도를 X축에, 부상 기간 또는 부상 일수를 Y축에 나타낸 산점도입니다.

    각 점은 한 선수의 데이터를 의미하며,
    점선을 통해 팔 각도와 부상 기간의 선형 관계를 확인할 수 있습니다.
    """
)

r2_duration = draw_regression_graph(
    analysis_df,
    "_팔각도",
    "_부상기간",
    "팔 각도와 부상 기간의 관계",
    "팔 각도 (°)",
    "부상 기간 / 일수"
)


# --------------------------------------------------
# 데이터 표
# --------------------------------------------------
st.divider()

st.header("📑 분석에 사용된 선수별 데이터")

result_df = pd.DataFrame({
    "선수": analysis_df["_선수명"],
    "팔 각도 (°)": analysis_df["_팔각도"],
    "부상 횟수 (회)": analysis_df["_부상횟수"],
    "부상 기간 / 일수": analysis_df["_부상기간"]
})

st.dataframe(
    result_df,
    use_container_width=True,
    hide_index=True
)

# CSV 다운로드
csv = result_df.to_csv(
    index=False,
    encoding="utf-8-sig"
)

st.download_button(
    label="📥 분석 데이터 CSV 다운로드",
    data=csv,
    file_name="팔각도_부상분석.csv",
    mime="text/csv"
)


# --------------------------------------------------
# 해석 안내
# --------------------------------------------------
st.divider()

st.header("💡 회귀분석 결과 해석하기")

st.markdown(
    """
    - **회귀선의 기울기**: 팔 각도가 증가할 때 부상 횟수 또는 부상 기간이 어떻게 변하는지 보여줍니다.
    - **양의 기울기**: 팔 각도가 커질수록 Y값이 증가하는 경향입니다.
    - **음의 기울기**: 팔 각도가 커질수록 Y값이 감소하는 경향입니다.
    - **R² (결정계수)**: 회귀모형이 데이터의 변동을 얼마나 설명하는지 나타냅니다. 1에 가까울수록 설명력이 높습니다.
    """
)

st.warning(
    "주의: 회귀분석은 변수 사이의 통계적 관계를 보여줄 뿐, "
    "팔 각도가 부상을 직접 일으킨다는 인과관계를 증명하지는 않습니다."
)

st.caption("팔 각도와 부상 관련 데이터 분석 앱")
