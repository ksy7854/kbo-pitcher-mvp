import streamlit as st
import pandas as pd

# 페이지 기본 설정
st.set_page_config(page_title="KBO Pitcher MVP Calculator", page_icon="⚾", layout="wide")

st.title("⚾ KBO 투수 MVP 자동 계산기")
st.caption("FIP, POPS, WHIP 지표 기반 투수 MVP 산출 프로그램")

st.markdown("""
---
### 📌 수정된 투수 MVP 평가 기준
* **MVP 점수 수식**: `- [ (FIP × 34.1%) + (POPS × 33.7%) + (WHIP × 32.2%) ]`
* **규정 이닝 기준**: `팀 경기 수 × 1.0` (기본 144이닝)
* **점수 특징**: 지표 수치가 낮을수록 뛰어난 투수이므로, 마이너스(-)를 적용하여 **0에 가까울수록(점수가 높을수록) 1위**입니다.
---
""")

# CSV 및 Excel 파일 업로드 모두 지원
uploaded_file = st.file_uploader("투수 성적 데이터(CSV 또는 Excel)를 업로드하세요", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    try:
        # 파일 확장자에 따른 데이터로드 및 한글 인코딩 분기 처리
        if uploaded_file.name.endswith(".csv"):
            try:
                df_pitcher = pd.read_csv(uploaded_file, encoding="utf-8")
            except:
                uploaded_file.seek(0)
                df_pitcher = pd.read_csv(uploaded_file, encoding="cp949")
        else:
            df_pitcher = pd.read_excel(uploaded_file)

        # 연도 선택
        years = sorted(df_pitcher["연도"].unique(), reverse=True)
        selected_year = st.selectbox("📅 시즌 선택", years)

        # 선택한 연도 데이터 필터링
        df_year = df_pitcher[df_pitcher["연도"] == selected_year].copy()

        # 규정 이닝 필터 옵션 (기본 144이닝)
        ip_limit = 144
        filter_ip = st.checkbox(f"규정 이닝({ip_limit}이닝) 이상 투수만 보기", value=True)

        if filter_ip and "이닝" in df_year.columns:
            df_year = df_year[df_year["이닝"] >= ip_limit]

        # 투수 MVP 점수 자동 계산 (가중치 적용: FIP 34.1%, POPS 33.7%, WHIP 32.2%)
        df_year["MVP_Score"] = -1 * (
            (df_year["FIP"] * 0.341) + 
            (df_year["POPS"] * 0.337) + 
            (df_year["WHIP"] * 0.322)
        ).round(4)

        # MVP 점수 내림차순 정렬 (0에 가까운 높은 순)
        df_year = df_year.sort_values(by="MVP_Score", ascending=False).reset_index(drop=True)
        df_year.index = df_year.index + 1

        # 결과 출력
        if not df_year.empty:
            top_pitcher = df_year.iloc[0]
            st.success(
                f"🏆 **{selected_year}시즌 모델 선정 투수 MVP**: "
                f"**{top_pitcher['선수명']}** ({top_pitcher['소속팀']}) | "
                f"MVP 점수: **{top_pitcher['MVP_Score']}**"
            )

            st.subheader(f"📊 {selected_year}시즌 투수 MVP 리더보드")
            
            show_cols = ["선수명", "소속팀", "FIP", "POPS", "WHIP", "MVP_Score"]
            if "이닝" in df_year.columns:
                show_cols.insert(2, "이닝")
            if "평균자책점" in df_year.columns:
                show_cols.insert(3, "평균자책점")

            st.dataframe(df_year[show_cols], use_container_width=True)
        else:
            st.warning("규정 이닝을 충족한 투수 데이터가 없습니다.")

    except Exception as e:
        st.error(f"파일을 읽는 도중 오류가 발생했습니다: {e}")
        st.info("💡 파일의 칼럼명(연도, 선수명, 소속팀, FIP, POPS, WHIP 등)이 올바른지 확인해 주세요.")

else:
    st.info("💡 분석을 시작하려면 투수 성적 CSV 또는 Excel 파일을 업로드해 주세요.")