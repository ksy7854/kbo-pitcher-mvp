import streamlit as st
import pandas as pd

st.set_page_config(page_title="KBO MVP 자동 계산기", page_icon="⚾", layout="wide")

st.title("⚾ KBO MVP 자동 계산기")
st.caption("통합 데이터(타자/투수) 지원 및 가중치 기반 MVP 산출 프로그램")

st.markdown("""
---
### 📌 MVP 평가 기준
* **타자 MVP 수식**: `(장타율 × 37.3%) + (타율 × 33.1%) + (출루율 × 29.6%)` (규정 446타석)
* **투수 MVP 수식**: `- [ (FIP × 34.1%) + (POPS × 33.7%) + (WHIP × 32.2%) ]` (규정 144이닝)
---
""")

uploaded_file = st.file_uploader("통합 성적 데이터(CSV 또는 Excel)를 업로드하세요", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    try:
        # 1. 파일 읽기 (엑셀일 경우 시트 선택 기능 추가)
        if uploaded_file.name.endswith(".csv"):
            try:
                df_raw = pd.read_csv(uploaded_file, encoding="utf-8")
            except:
                uploaded_file.seek(0)
                df_raw = pd.read_csv(uploaded_file, encoding="cp949")
        else:
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
            
            # 시트가 여러 개일 경우 선택 창 표시
            if len(sheet_names) > 1:
                selected_sheet = st.selectbox("📄 분석할 시트(Sheet)를 선택하세요", sheet_names)
            else:
                selected_sheet = sheet_names[0]
                
            df_raw = pd.read_excel(uploaded_file, sheet_name=selected_sheet)

        # 2. 타자/투수 구분 로직
        # '구분'이나 '포지션' 칼럼이 있거나 지표 컬럼으로 구분
        cols = df_raw.columns.tolist()
        
        is_pitcher = any(col in cols for col in ["FIP", "POPS", "WHIP", "피OPS", "평균자책점"])
        is_hitter = any(col in cols for col in ["타율", "출루율", "장타율", "SLG", "OBP"])

        # 포지션 선택 radio 버튼 (자동 추정 지원)
        default_idx = 0 if is_hitter and not is_pitcher else (1 if is_pitcher else 0)
        mode = st.radio("분석 대상을 선택하세요", ["🏏 타자", "⚾ 투수"], index=default_idx, horizontal=True)

        # '구분' 또는 '포지션' 열이 통합 데이터에 있을 경우 필터링
        if "구분" in df_raw.columns:
            if mode == "🏏 타자":
                df_data = df_raw[df_raw["구분"].str.contains("타자|타", na=False)].copy()
            else:
                df_data = df_raw[df_raw["구분"].str.contains("투수|투", na=False)].copy()
        else:
            df_data = df_raw.copy()

        # 연도 선택
        if "연도" in df_data.columns:
            years = sorted(df_data["연도"].unique(), reverse=True)
            selected_year = st.selectbox("📅 시즌 선택", years)
            df_year = df_data[df_data["연도"] == selected_year].copy()
        else:
            st.error("데이터에 '연도' 컬럼이 존재하지 않습니다.")
            st.stop()

        # ==========================================
        # 타자 MVP 계산
        # ==========================================
        if mode == "🏏 타자":
            filter_pa = st.checkbox("규정 타석(446타석) 이상만 보기", value=True)
            if filter_pa and "타석" in df_year.columns:
                df_year = df_year[df_year["타석"] >= 446]

            # 컬럼명 유연성 확보 (장타율/SLG 등)
            avg_col = "타율" if "타율" in df_year.columns else "AVG"
            obp_col = "출루율" if "출루율" in df_year.columns else "OBP"
            slg_col = "장타율" if "장타율" in df_year.columns else "SLG"

            df_year["MVP_Score"] = (
                (df_year[slg_col] * 0.373) + 
                (df_year[avg_col] * 0.331) + 
                (df_year[obp_col] * 0.296)
            ).round(4)

            df_year = df_year.sort_values(by="MVP_Score", ascending=False).reset_index(drop=True)
            df_year.index = df_year.index + 1

            if not df_year.empty:
                top = df_year.iloc[0]
                st.success(f"🏆 **{selected_year}시즌 모델 선정 타자 MVP**: **{top['선수명']}** ({top['소속팀']}) | 점수: **{top['MVP_Score']}**")
                
                show_cols = ["선수명", "소속팀", avg_col, obp_col, slg_col, "MVP_Score"]
                if "타석" in df_year.columns: show_cols.insert(2, "타석")
                st.dataframe(df_year[show_cols], use_container_width=True)

        # ==========================================
        # 투수 MVP 계산
        # ==========================================
        else:
            filter_ip = st.checkbox("규정 이닝(144이닝) 이상만 보기", value=True)
            if filter_ip and "이닝" in df_year.columns:
                df_year = df_year[df_year["이닝"] >= 144]

            pops_col = "POPS" if "POPS" in df_year.columns else "피OPS"

            df_year["MVP_Score"] = -1 * (
                (df_year["FIP"] * 0.341) + 
                (df_year[pops_col] * 0.337) + 
                (df_year["WHIP"] * 0.322)
            ).round(4)

            df_year = df_year.sort_values(by="MVP_Score", ascending=False).reset_index(drop=True)
            df_year.index = df_year.index + 1

            if not df_year.empty:
                top = df_year.iloc[0]
                st.success(f"🏆 **{selected_year}시즌 모델 선정 투수 MVP**: **{top['선수명']}** ({top['소속팀']}) | 점수: **{top['MVP_Score']}**")
                
                show_cols = ["선수명", "소속팀", "FIP", pops_col, "WHIP", "MVP_Score"]
                if "이닝" in df_year.columns: show_cols.insert(2, "이닝")
                st.dataframe(df_year[show_cols], use_container_width=True)

    except Exception as e:
        st.error(f"파일을 읽는 도중 오류가 발생했습니다: {e}")
        st.info("💡 엑셀 시트 이름을 확인하거나 타자/투수 라디오 버튼을 전환해 보세요.")

else:
    st.info("💡 분석을 시작하려면 타자/투수 통합 엑셀 또는 CSV 파일을 업로드해 주세요.")
