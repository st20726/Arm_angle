
import streamlit as st
import pandas as pd
import plotly.express as px
import re

# ---------------------------------------
# 페이지 설정
# ---------------------------------------
st.set_page_config(
    page_title="팔각도와 부상기간, 부상 일수",
    page_icon="⚾",
    layout="wide"
)

st.title("⚾ 팔각도와 부상기간, 부상 일수")
st.write(
    "선수별 팔 각도와 부상 횟수 및 부상 일수의 관계를 "
    "산점도로 확인하는 앱입니다."
)

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
def load_data(header_row):
    df = pd.read_csv(
        GOOGLE_CSV_URL,
        encoding="utf-8-sig",
        header=header_row,
        engine="python"
    )

    # 완전히 비어 있는 행과 열 제거
    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")

    # 열 이름의 앞뒤 공백 제거
    df.columns = [
        str(col).strip()
        for col in df.columns
    ]

    return df


# ---------------------------------------
# 열 선택 함수
# ---------------------------------------
def find_column(columns, candidates):
    for candidate in candidates:
        for col in columns:
            if candidate.lower() == str(col).lower():
                return col

    for candidate in candidates:
        for col in columns:
            if candidate.lower() in str(col).lower():
                return col

    return None


def select_column(label, columns, candidates=None, optional=False):
    candidates = candidates or []
    matched = find_column(columns, candidates)

    options = list(columns)

    if optional:
        options = ["선택 안 함"] + options

    default_index = 0

    if matched in options:
        default_index = options.index(matched)
    elif optional:
        default_index = 0

    return st.selectbox(
        label,
        options,
        index=default_index
    )


# ---------------------------------------
# 숫자 변환 함수
# ---------------------------------------
def convert_number(series):
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("일", "", regex=False)
        .str.replace("°", "", regex=False)
        .str.replace("명", "", regex=False)
        .str.strip()
    )

    cleaned = cleaned.replace(
        ["", "nan", "None", "-", "없음"],
        pd.NA
    )

    return pd.to_numeric(cleaned, errors="coerce")


# ---------------------------------------
# 데이터 불러오기 화면
# ---------------------------------------
st.subheader("1. 데이터 확인")

header_row = st.number_input(
    "열 이름이 있는 행 번호 (첫 번째 행은 0)",
    min_value=0,
    max_value=20,
    value=0,
    step=1,
    help="스프레드시트의 첫 번째 행에 열 이름이 있다면 0을 그대로 사용하세요."
)

try:
    df = load_data(int(header_row))

except Exception as e:
    st.error("데이터를 불러오지 못했습니다.")
    st.write("다음 사항을 확인해 주세요.")
    st.markdown(
        """
        - 구글 스프레드시트 공유 설정이 '링크가 있는 사용자 - 뷰어'인지 확인
        - 데이터가 있는 시트의 GID가 맞는지 확인
        - 첫 번째 행 또는 선택한 행에 열 이름이 있는지 확인
        - 셀 안에 쉼표가 포함된 경우 데이터가 정상적으로 입력되어 있는지 확인
        """
    )
    st.code(str(e))
    st.stop()


if df.empty:
    st.error("불러온 데이터가 비어 있습니다.")
    st.stop()


st.success("데이터를 불러왔습니다.")

with st.expander("원본 데이터 미리 보기"):
    st.write(f"데이터 크기: {df.shape[0]}행 × {df.shape[1]}열")
    st.dataframe(df, use_container_width=True)

# ---------------------------------------
# 열 설정
# ---------------------------------------
st.subheader("2. 데이터 열 선택")

st.info(
    "실제 데이터의 열 이름에 맞게 아래 항목을 선택해 주세요. "
    "자동으로 선택된 열도 반드시 확인해 주세요."
)

columns = list(df.columns)

col1, col2 = st.columns(2)

with col1:
    player_col = select_column(
        "선수 이름 열",
        columns,
        ["선수명", "선수", "이름", "player", "name"]
    )

    angle_col = select_column(
        "팔 각도 열",
        columns,
        ["팔각도", "팔 각도", "각도", "arm angle", "angle"]
    )

with col2:
    duration_col = select_column(
        "부상 일수 열",
        columns,
        ["부상일수", "부상 일수", "부상기간", "부상 기간",
         "기간", "injury days", "duration", "days"]
    )

    count_col = select_column(
        "부상 횟수 열 (없으면 선택 안 함)",
        columns,
        ["부상횟수", "부상 횟수", "부상수", "injury count",
         "injuries", "count"],
        optional=True
    )

# ---------------------------------------
# 데이터 형태 선택
# ---------------------------------------
st.subheader("3. 데이터 형태")

data_type = st.radio(
    "스프레드시트의 데이터는 어떤 형태인가요?",
    [
        "선수별 요약 데이터",
        "부상 기록별 데이터"
    ],
    help=(
        "선수별 요약 데이터: 선수 한 명당 한 행으로 정리된 자료\n"
        "부상 기록별 데이터: 부상 사건 하나당 한 행으로 정리된 자료"
    )
)

if data_type == "선수별 요약 데이터" and count_col == "선택 안 함":
    st.warning(
        "선수별 요약 데이터에서는 부상 횟수 열을 선택해야 합니다. "
        "부상 횟수가 들어 있는 열을 지정해 주세요."
    )
    st.stop()


# ---------------------------------------
# 분석용 데이터 만들기
# ---------------------------------------
work = df.copy()

work["선수"] = work[player_col].astype("string").str.strip()
work["팔 각도"] = convert_number(work[angle_col])
work["부상 일수"] = convert_number(work[duration_col])

if count_col != "선택 안 함":
    work["부상 횟수"] = convert_number(work[count_col])
else:
    # 부상 기록별 데이터에서는 한 행을 부상 1건으로 계산
    work["부상 횟수"] = 1


# 선수 이름 없는 행 제거
work = work.dropna(subset=["선수", "팔 각도"])
work = work[
    (work["선수"] != "")
    & (work["선수"].str.lower() != "nan")
]

# 팔 각도 범위 확인
invalid_angle = ~work["팔 각도"].between(0, 180)

invalid_count = int(invalid_angle.sum())

if invalid_count > 0:
    st.warning(
        f"팔 각도가 0~180도 범위를 벗어난 데이터 "
        f"{invalid_count}개를 분석에서 제외했습니다."
    )

work = work[work["팔 각도"].between(0, 180)].copy()

if work.empty:
    st.error(
        "분석할 수 있는 데이터가 없습니다. "
        "팔 각도 열을 올바르게 선택했는지 확인해 주세요."
    )
    st.stop()


# 부상 일수 결측값은 합계 계산에서 제외
work["부상 일수"] = work["부상 일수"].fillna(0)

# 부상 횟수 결측값 처리
work["부상 횟수"] = work["부상 횟수"].fillna(0)

# 음수 값 제거
work.loc[work["부상 일수"] < 0, "부상 일수"] = 0
work.loc[work["부상 횟수"] < 0, "부상 횟수"] = 0


# ---------------------------------------
# 선수별 집계
# ---------------------------------------
if data_type == "부상 기록별 데이터":
    # 한 행이 부상 한 건이므로 선수별 행 개수를 계산
    if count_col == "선택 안 함":
        work["부상 횟수"] = 1

    result = (
        work.groupby("선수")
        .agg(
            팔각도=("팔 각도", "mean"),
            부상횟수=("부상 횟수", "sum"),
            부상일수=("부상 일수", "sum")
        )
        .reset_index()
    )

else:
    # 선수별 요약 데이터는 중복 선수명이 있으면 합산
    result = (
        work.groupby("선수")
        .agg(
            팔각도=("팔 각도", "mean"),
            부상횟수=("부상 횟수", "sum"),
            부상일수=("부상 일수", "sum")
        )
        .reset_index()
    )


# 분석 가능한 숫자 데이터만 사용
result = result.replace(
    [float("inf"), float("-inf")],
    pd.NA
)

result = result.dropna(
    subset=["팔각도", "부상횟수", "부상일수"]
)

if result.empty:
    st.error("집계 후 분석할 데이터가 없습니다.")
    st.stop()


# ---------------------------------------
# 분석 결과
# ---------------------------------------
st.subheader("4. 선수별 분석 데이터")

st.write(
    f"분석에 사용된 선수 수: **{len(result)}명**"
)

st.dataframe(
    result.rename(
        columns={
            "선수": "선수명",
            "팔각도": "팔 각도(도)",
            "부상횟수": "부상 횟수",
            "부상일수": "부상 일수"
        }
    ).round(2),
    use_container_width=True,
    hide_index=True
)


# ---------------------------------------
# 그래프 1
# ---------------------------------------
st.divider()
st.subheader("5. 팔 각도와 부상 횟수의 관계")

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
        "팔각도": "팔 각도 (도)",
        "부상횟수": "부상 횟수"
    },
    title="선수별 팔 각도와 부상 횟수"
)

fig1.update_traces(
    marker=dict(size=11, opacity=0.8)
)

fig1.update_layout(
    height=550,
    xaxis_title="팔 각도 (도)",
    yaxis_title="부상 횟수",
    hovermode="closest"
)

st.plotly_chart(
    fig1,
    use_container_width=True
)

st.caption(
    "점 하나가 선수 한 명을 나타냅니다. "
    "점에 마우스를 올리면 선수 이름과 데이터를 확인할 수 있습니다."
)


# ---------------------------------------
# 그래프 2
# ---------------------------------------
st.divider()
st.subheader("6. 팔 각도와 부상 일수의 관계")

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
        "팔각도": "팔 각도 (도)",
        "부상일수": "부상 일수"
    },
    title="선수별 팔 각도와 부상 일수"
)

fig2.update_traces(
    marker=dict(size=11, opacity=0.8)
)

fig2.update_layout(
    height=550,
    xaxis_title="팔 각도 (도)",
    yaxis_title="부상 일수",
    hovermode="closest"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)

st.caption(
    "점 하나가 선수 한 명을 나타냅니다. "
    "점에 마우스를 올리면 선수 이름과 데이터를 확인할 수 있습니다."
)


# ---------------------------------------
# 데이터 다운로드
# ---------------------------------------
st.divider()
st.subheader("7. 분석 데이터 다운로드")

csv = result.rename(
    columns={
        "선수": "선수명",
        "팔각도": "팔 각도(도)",
        "부상횟수": "부상 횟수",
        "부상일수": "부상 일수"
    }
).to_csv(index=False, encoding="utf-8-sig")

st.download_button(
    label="분석 결과 CSV 다운로드",
    data=csv,
    file_name="팔각도_부상분석.csv",
    mime="text/csv"
)

st.info(
    "이 앱은 산점도만 표시하며 회귀선이나 회귀분석 결과는 추가하지 않았습니다. "
    "산점도는 두 변수 사이의 관계를 살펴보는 자료이며, "
    "그 자체만으로 팔 각도가 부상의 원인이라고 판단할 수는 없습니다."
)
