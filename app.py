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

# 컬럼명 유연하게 찾아주는 함수
def find_column(df, possible_names, default=None):
    for name in possible_names:
        for col in df.columns:
            if name.lower() in str(col).lower().strip():
                return col
    return default

uploaded_file = st.file_uploader("통합 성적 데이터(CSV 또는 Excel)를 업로드하세요", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    try:
        # 1. 파일 및 시트 읽기
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

        # 2. 타자/투수 구분 로직
        cols = [str(c).strip() for c in df_raw.columns]
        is_pitcher = any(col in cols for col in ["FIP", "POPS", "WHIP", "피OPS", "평균자책점", "ERA"])
        is_hitter = any(col in cols for col in ["타율", "출루율", "장타율", "SLG", "OBP", "AVG"])

        default_idx = 0 if is_hitter and not is_pitcher else (1 if is_pitcher else 0)
        mode = st.radio("분석 대상을 선택하세요", ["🏏 타자", "⚾ 투수"], index=default_idx, horizontal=True)

        # '구분' 또는 '포지션' 열이 있을 경우 필터링
        cat_col = find_column(df_raw, ["구분", "포지션", "Position"])
        if cat_col:
            if mode == "🏏 타자":
                df_data = df_raw[df_raw[cat_col].astype(str).str.contains("타자|타", na=False)].copy()
            else:
                df_data = df_raw[df_raw[cat_col].astype(str).str.contains("투수|투", na=False)].copy()
        else:
            df_data = df_raw.copy()

        # 연도 컬럼 찾기
        year_col = find_column(df_data, ["연도", "시즌", "Year", "Season"])
        if year_col:
            years = sorted(df_data[year_col].unique(), reverse=True)
            selected_year = st.selectbox("📅 시즌 선택", years)
            df_year = df_data[df_data[year_col] == selected_year].copy()
        else:
            st.error("데이터에서 '연도' 또는 '시즌' 컬럼을 찾을 수 없습니다.")
            st.stop()

        # 공통 컬럼 유연하게 검색 (선수명, 소속팀)
        name_col = find_column(df_year, ["선수명", "이름", "선수", "Name"], default=df_year.columns[0])
        team_col = find_column(df_year, ["소속팀", "팀명", "팀", "Team"], default=None)

        # ==========================================
        # 타자 MVP 계산
        # ==========================================
        if mode == "🏏 타자":
            filter_pa = st.checkbox("규정 타석(446타석) 이상만 보기", value=True)
            pa_col = find_column(df_year, ["타석", "PA"])
            if filter_pa and pa_col:
                df_year = df_year[df_year[pa_col] >= 446]

            avg_col = find_column(df_year, ["타율", "AVG"])
            obp_col = find_column(df_year, ["출루율", "OBP"])
            slg_col = find_column(df_year, ["장타율", "SLG"])

            if not (avg_col and obp_col and slg_col):
                st.error("타자 지표(타율, 출루율, 장타율) 컬럼이 부족합니다.")
                st.stop()

            df_year["MVP_Score"] = (
                (df_year[slg_col] * 0.373) + 
                (df_year[avg_col] * 0.331) + 
                (df_year[obp_col] * 0.296)
            ).round(4)

            df_year = df_year.sort_values(by="MVP_Score", ascending=False).reset_index(drop=True)
            df_year.index = df_year.index + 1

            if not df_year.empty:
                top = df_year.iloc[0]
                team_str = f" ({top[team_col]})" if team_col else ""
                st.success(f"🏆 **{selected_year}시즌 모델 선정 타자 MVP**: **{top[name_col]}**{team_str} | 점수: **{top['MVP_Score']}**")
                
                show_cols = [name_col]
                if team_col: show_cols.append(team_col)
                if pa_col: show_cols.append(pa_col)
                show_cols.extend([avg_col, obp_col, slg_col, "MVP_Score"])
                
                st.dataframe(df_year[show_cols], use_container_width=True)

        # ==========================================
        # 투수 MVP 계산
        # ==========================================
        else:
            filter_ip = st.checkbox("규정 이닝(144이닝) 이상만 보기", value=True)
            ip_col = find_column(df_year, ["이닝", "IP"])
            if filter_ip and ip_col:
                df_year = df_year[df_year[ip_col] >= 144]

            fip_col = find_column(df_year, ["FIP"])
            pops_col = find_column(df_year, ["POPS", "피OPS", "피_OPS"])
            whip_col = find_column(df_year, ["WHIP"])

            if not (fip_col and pops_col and whip_col):
                st.error("투수 지표(FIP, POPS, WHIP) 컬럼이 부족합니다.")
                st.stop()

            df_year["MVP_Score"] = -1 * (
                (df_year[fip_col] * 0.341) + 
                (df_year[pops_col] * 0.337) + 
                (df_year[whip_col] * 0.322)
            ).round(4)

            df_year = df_year.sort_values(by="MVP_Score", ascending=False).reset_index(drop=True)
            df_year.index = df_year.index + 1

            if not df_year.empty:
                top = df_year.iloc[0]
                team_str = f" ({top[team_col]})" if team_col else ""
                st.success(f"🏆 **{selected_year}시즌 모델 선정 투수 MVP**: **{top[name_col]}**{team_str} | 점수: **{top['MVP_Score']}**")
                
                show_cols = [name_col]
                if team_col: show_cols.append(team_col)
                if ip_col: show_cols.append(ip_col)
                show_cols.extend([fip_col, pops_col, whip_col, "MVP_Score"])
                
                st.dataframe(df_year[show_cols], use_container_width=True)

    except Exception as e:
        st.error(f"파일 처리 중 오류 발생: {e}")

else:
    st.info("💡 분석을 시작하려면 성적 데이터를 업로드해 주세요.")
