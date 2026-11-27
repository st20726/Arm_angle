
import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------
# 페이지 설정
# ---------------------------------------
st.set_page_config(
    page_title="팔각도와 부상기간, 부상 일수",
    page_icon="⚾",
    layout="wide"
)

st.title("⚾ 팔각도와 부상기간, 부상 일수")
st.write("선수별 팔 각도와 부상 횟수 및 부상 일수의 관계를 알아봅니다.")

# ---------------------------------------
# 구글 스프레드시트 주소
# ---------------------------------------
GOOGLE_SHEET_ID = "1I0jc_dkPFAqInxhxaKKccfLjQ8na9TKx"
GID = "1503298569"

GOOGLE_CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
    f"/export?format=csv&gid={GID}"
)

# ---------------------------------------
# 데이터 불러오기
# ---------------------------------------
@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(
        GOOGLE_CSV_URL,
        encoding="utf-8-sig",
        engine="python",
        on_bad_lines="warn"
    )

    df.columns = [str(col).strip() for col in df.columns]
    return df


try:
    df = load_data()

except Exception as e:
    st.error("데이터를 불러오지 못했습니다.")
    st.write("구글 스프레드시트 공유 설정을 확인해 주세요.")
    st.code(str(e))
    st.stop()


# ---------------------------------------
# 필요한 열 지정
# ---------------------------------------
PLAYER_COL = "Unnamed: 1"
ANGLE_COL = "Unnamed: 6"
COUNT_COL = "Unnamed: 9"
DAYS_COL = "Unnamed: 10"

required_columns = [
    PLAYER_COL,
    ANGLE_COL,
    COUNT_COL,
    DAYS_COL
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    st.error("필요한 데이터 열을 찾을 수 없습니다.")
    st.write("찾지 못한 열:", missing_columns)
    st.write("현재 데이터의 열 이름:")
    st.write(list(df.columns))
    st.stop()


# ---------------------------------------
# 숫자 데이터 변환
# ---------------------------------------
def to_number(series):
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("°", "", regex=False)
        .str.replace("일", "", regex=False)
        .str.strip()
    )

    cleaned = cleaned.replace(
        ["", "nan", "None", "-", "없음"],
        pd.NA
    )

    return pd.to_numeric(cleaned, errors="coerce")


# ---------------------------------------
# 분석용 데이터 구성
# ---------------------------------------
data = pd.DataFrame()

data["선수"] = df[PLAYER_COL].astype("string").str.strip()
data["팔각도"] = to_number(df[ANGLE_COL])
data["부상횟수"] = to_number(df[COUNT_COL])
data["부상일수"] = to_number(df[DAYS_COL])

# 선수 이름이 없는 행 제거
data = data.dropna(subset=["선수", "팔각도"])
data = data[
    (data["선수"] != "")
    & (data["선수"].str.lower() != "nan")
]

# ---------------------------------------
# 팔 각도 -180도 ~ 180도 범위 적용
# ---------------------------------------
invalid_angle = ~data["팔각도"].between(-180, 180)
invalid_count = int(invalid_angle.sum())

data = data[
    data["팔각도"].between(-180, 180)
].copy()

if invalid_count > 0:
    st.warning(
        f"팔 각도가 -180~180도 범위를 벗어난 "
        f"{invalid_count}개 행은 제외했습니다."
    )

# ---------------------------------------
# 부상 횟수와 부상 일수 결측값 처리
# ---------------------------------------
data["부상횟수"] = data["부상횟수"].fillna(0)
data["부상일수"] = data["부상일수"].fillna(0)

# 음수 부상 데이터 제거
data.loc[data["부상횟수"] < 0, "부상횟수"] = 0
data.loc[data["부상일수"] < 0, "부상일수"] = 0

if data.empty:
    st.error("분석할 수 있는 데이터가 없습니다.")
    st.stop()


# ---------------------------------------
# 선수별 데이터 집계
# ---------------------------------------
result = (
    data.groupby("선수")
    .agg(
        팔각도=("팔각도", "mean"),
        부상횟수=("부상횟수", "sum"),
        부상일수=("부상일수", "sum")
    )
    .reset_index()
)

if result.empty:
    st.error("집계 후 분석할 데이터가 없습니다.")
    st.stop()


# ---------------------------------------
# 데이터 요약
# ---------------------------------------
st.subheader("📋 선수별 데이터")

st.write(f"분석 대상 선수 수: **{len(result)}명**")

st.dataframe(
    result.rename(
        columns={
            "선수": "선수 이름",
            "팔각도": "팔 각도(도)",
            "부상횟수": "부상 횟수",
            "부상일수": "부상 일수"
        }
    ).round(2),
    use_container_width=True,
    hide_index=True
)


# ---------------------------------------
# 그래프 1: 팔 각도와 부상 횟수
# ---------------------------------------
st.divider()
st.subheader("📊 팔 각도와 부상 횟수의 관계")

fig1 = px.scatter(
    result,
    x="팔각도",
    y="부상횟수",
    hover_name="선수",
    hover_data={
        "팔각도": ":.2f",
        "부상횟수": True,
        "부상일수": True
    },
    labels={
        "팔각도": "팔 각도(도)",
        "부상횟수": "부상 횟수"
    },
    title="선수별 팔 각도와 부상 횟수"
)

fig1.update_traces(
    marker=dict(size=11, opacity=0.8)
)

fig1.update_layout(
    height=550,
    xaxis_title="팔 각도(도)",
    yaxis_title="부상 횟수"
)

st.plotly_chart(
    fig1,
    use_container_width=True
)


# ---------------------------------------
# 그래프 2: 팔 각도와 부상 일수
# ---------------------------------------
st.divider()
st.subheader("📊 팔 각도와 부상 일수의 관계")

fig2 = px.scatter(
    result,
    x="팔각도",
    y="부상일수",
    hover_name="선수",
    hover_data={
        "팔각도": ":.2f",
        "부상횟수": True,
        "부상일수": True
    },
    labels={
        "팔각도": "팔 각도(도)",
        "부상일수": "부상 일수"
    },
    title="선수별 팔 각도와 부상 일수"
)

fig2.update_traces(
    marker=dict(size=11, opacity=0.8)
)

fig2.update_layout(
    height=550,
    xaxis_title="팔 각도(도)",
    yaxis_title="부상 일수"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)
