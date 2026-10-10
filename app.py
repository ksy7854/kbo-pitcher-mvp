import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="KBO 투수 MVP 자동 계산기", page_icon="⚾", layout="wide")

st.title("⚾ KBO 투수 MVP 자동 계산기")
st.caption("FIP, POPS, WHIP 지표 가중합 모델 기반 MVP 산출 프로그램")

st.markdown("""
---
### 📌 투수 MVP 평가 모델 기준
* **MVP 점수 수식**: `- [ (FIP × 34.1%) + (POPS × 33.7%) + (WHIP × 32.2%) ]`[cite: 2]
* **규정 이닝 기준**: `팀 경기 수 × 1.0` (기본 144이닝)
* **점수 특징**: 지표 수치가 낮을수록 뛰어난 투수이므로, 마이너스(-)를 적용하여 **0에 가까울수록(점수가 높을수록) 1위**입니다.
---
""")

# 칼럼명 자동 탐색 함수
def find_column(df, possible_names, default=None):
    for name in possible_names:
        for col in df.columns:
            if name.lower() in str(col).lower().strip():
                return col
    return default

# 파일 업로드 (CSV 및 Excel 지원)
uploaded_file = st.file_uploader("투수 성적 데이터(CSV 또는 Excel)를 업로드하세요", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    try:
        # 1. 파일 읽기 및 시트 선택
        if uploaded_file.name.endswith(".csv"):
            try:
                df_raw = pd.read_csv(uploaded_file, encoding="utf-8")
            except:
                uploaded_file.seek(0)
                df_raw = pd.read_csv(uploaded_file, encoding="cp949")
        else:
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
            
            if len(sheet_names) > 1:
                selected_sheet = st.selectbox("📄 분석할 시트(Sheet)를 선택하세요", sheet_names)
            else:
                selected_sheet = sheet_names[0]
                
            df_raw = pd.read_excel(uploaded_file, sheet_name=selected_sheet)

        # 2. 연도/시즌 컬럼 감지
        year_col = find_column(df_raw, ["연도", "시즌", "Year", "Season"])
        if not year_col:
            st.error("데이터에서 '연도' 또는 '시즌' 컬럼을 찾을 수 없습니다. 데이터 시트를 다시 확인해 주세요.")
            st.stop()

        years = sorted(df_raw[year_col].unique(), reverse=True)
        selected_year = st.selectbox("📅 시즌 선택", years)
        df_year = df_raw[df_raw[year_col] == selected_year].copy()

        # 3. 주요 칼럼 감지 (선수명, 소속팀, 이닝)
        name_col = find_column(df_year, ["선수명", "이름", "선수", "Name"], default=df_year.columns[0])
        team_col = find_column(df_year, ["소속팀", "팀명", "팀", "Team"])
        ip_col = find_column(df_year, ["이닝", "IP"])

        # 4. 규정 이닝 필터링 옵션
        if ip_col:
            filter_ip = st.checkbox("규정 이닝(144이닝) 이상 투수만 보기", value=True)
            if filter_ip:
                df_year = df_year[df_year[ip_col] >= 144]

        # 5. 핵심 투수 지표 컬럼 감지
        fip_col = find_column(df_year, ["FIP"])
        pops_col = find_column(df_year, ["POPS", "피OPS", "피_OPS"])
        whip_col = find_column(df_year, ["WHIP"])

        if not (fip_col and pops_col and whip_col):
            st.error("투수 지표(FIP, POPS, WHIP) 컬럼이 부족합니다. 엑셀 헤더명을 확인해 주세요.")
            st.stop()

        # 6. MVP 점수 계산 (FIP 34.1%, POPS 33.7%, WHIP 32.2%)[cite: 2]
        df_year["MVP_Score"] = -1 * (
            (df_year[fip_col] * 0.341) + 
            (df_year[pops_col] * 0.337) + 
            (df_year[whip_col] * 0.322)
        ).round(4)

        # 7. 내림차순 정렬 (0에 가까울수록 1위)
        df_year = df_year.sort_values(by="MVP_Score", ascending=False).reset_index(drop=True)
        df_year.index = df_year.index + 1

        # 8. 결과 및 리더보드 출력
        if not df_year.empty:
            top_pitcher = df_year.iloc[0]
            team_str = f" ({top_pitcher[team_col]})" if team_col else ""
            st.success(
                f"🏆 **{selected_year}시즌 모델 선정 투수 MVP**: "
                f"**{top_pitcher[name_col]}**{team_str} | "
                f"MVP 점수: **{top_pitcher['MVP_Score']}**"
            )

            st.subheader(f"📊 {selected_year}시즌 투수 MVP 리더보드")
            
            show_cols = [name_col]
            if team_col: show_cols.append(team_col)
            if ip_col: show_cols.append(ip_col)
            
            era_col = find_column(df_year, ["평균자책점", "평균자책", "ERA"])
            if era_col: show_cols.append(era_col)
            
            show_cols.extend([fip_col, pops_col, whip_col, "MVP_Score"])
            st.dataframe(df_year[show_cols], use_container_width=True)
        else:
            st.warning("선택한 조건(규정 이닝 등)을 충족하는 투수 데이터가 없습니다.")

    except Exception as e:
        st.error(f"파일을 읽는 도중 오류가 발생했습니다: {e}")

else:
    st.info("💡 분석을 시작하려면 투수 성적 CSV 또는 Excel 파일을 업로드해 주세요.")
