import streamlit as st
import pandas as pd
import os

# 페이지 기본 설정
st.set_page_config(page_title="KBO 투수 MVP 자동 계산 및 대조기", page_icon="⚾", layout="wide")

st.title("⚾ KBO 투수 MVP 모델 vs 실제 수상자 대조기")
st.caption("FIP, POPS, WHIP 가중합 모델 산출 1위와 실제 MVP 비교 분석 프로그램")

st.markdown("""
---
### 📌 모델 평가 수식 및 가중치
* **MVP 점수 수식**: `- [ (FIP × 34.1%) + (POPS × 33.7%) + (WHIP × 32.2%) ]`[cite: 2]
* **규정 이닝 기준**: `팀 경기 수 × 1.0` (기본 144이닝)
* **점수 특징**: 지표 수치가 낮을수록 우수하므로 마이너스(-) 적용 $\rightarrow$ **0에 가까울수록(높을수록) 1위**
---
""")

# 칼럼명 자동 탐색 함수
def find_column(df, possible_names, default=None):
    for name in possible_names:
        for col in df.columns:
            if name.lower() in str(col).lower().strip():
                return col
    return default

# 폴더 내에 존재하는 데이터 파일(.xlsx, .csv) 자동 탐색
DEFAULT_FILES = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.csv', '.xls')) and not f.startswith('.')]

df_raw = None

# 사이드바에서 데이터 업로드 / 자동 로드 선택 옵션
st.sidebar.header("📁 데이터 설정")
use_uploaded = st.sidebar.checkbox("내 컴퓨터에서 파일 직접 올리기", value=False)

if use_uploaded:
    uploaded_file = st.file_uploader("투수 성적 데이터(CSV 또는 Excel)를 업로드하세요", type=["csv", "xlsx", "xls"])
    if uploaded_file is not None:
        if uploaded_file.name.endswith(".csv"):
            try:
                df_raw = pd.read_csv(uploaded_file, encoding="utf-8")
            except:
                uploaded_file.seek(0)
                df_raw = pd.read_csv(uploaded_file, encoding="cp949")
        else:
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
            selected_sheet = st.selectbox("📄 분석할 시트(Sheet)를 선택하세요", sheet_names) if len(sheet_names) > 1 else sheet_names[0]
            df_raw = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
else:
    # 깃허브/프로젝트 폴더 내 파일 자동 읽기
    if DEFAULT_FILES:
        selected_file = st.sidebar.selectbox("📂 프로젝트 데이터 파일 선택", DEFAULT_FILES) if len(DEFAULT_FILES) > 1 else DEFAULT_FILES[0]
        st.info(f"📂 프로젝트 데이터 파일 (**`{selected_file}`**)을 자동으로 불러왔습니다.")
        
        if selected_file.endswith(".csv"):
            try:
                df_raw = pd.read_csv(selected_file, encoding="utf-8")
            except:
                df_raw = pd.read_csv(selected_file, encoding="cp949")
        else:
            excel_file = pd.ExcelFile(selected_file)
            sheet_names = excel_file.sheet_names
            
            # 시트 중 '투수'가 들어간 시트를 기본값으로 자동 선택
            default_sheet_idx = 0
            for idx, s in enumerate(sheet_names):
                if "투수" in s:
                    default_sheet_idx = idx
                    break
            
            selected_sheet = st.selectbox("📄 분석할 시트(Sheet)를 선택하세요", sheet_names, index=default_sheet_idx) if len(sheet_names) > 1 else sheet_names[0]
            df_raw = pd.read_excel(selected_file, sheet_name=selected_sheet)
    else:
        st.warning("폴더 안에 기본 데이터 파일이 없습니다. 데이터 엑셀/CSV 파일을 app.py와 같은 폴더에 넣고 깃허브에 같이 올려주세요.")

if df_raw is not None:
    try:
        # 연도/시즌 칼럼 감지
        year_col = find_column(df_raw, ["연도", "시즌", "Year", "Season"])
        if not year_col:
            st.error("데이터에서 '연도' 또는 '시즌' 컬럼을 찾을 수 없습니다.")
            st.stop()

        years = sorted(df_raw[year_col].unique(), reverse=True)
        selected_year = st.selectbox("📅 시즌 선택", years)
        df_year = df_raw[df_raw[year_col] == selected_year].copy()

        # 주요 칼럼 감지
        name_col = find_column(df_year, ["선수명", "이름", "선수", "Name"], default=df_year.columns[0])
        team_col = find_column(df_year, ["소속팀", "팀명", "팀", "Team"])
        ip_col = find_column(df_year, ["이닝", "IP"])
        actual_mvp_col = find_column(df_year, ["실제MVP", "실제 수상자", "MVP수상자", "MVP"])

        # 규정 이닝 필터링
        if ip_col:
            filter_ip = st.checkbox("규정 이닝(144이닝) 이상 투수만 보기", value=True)
            if filter_ip:
                df_year = df_year[df_year[ip_col] >= 144]

        # 핵심 지표 감지 및 점수 계산
        fip_col = find_column(df_year, ["FIP"])
        pops_col = find_column(df_year, ["POPS", "피OPS", "피_OPS"])
        whip_col = find_column(df_year, ["WHIP"])

        if not (fip_col and pops_col and whip_col):
            st.error("투수 지표(FIP, POPS, WHIP) 컬럼이 부족합니다.")
            st.stop()

        # MVP 점수 산출 (FIP 34.1%, POPS 33.7%, WHIP 32.2%)[cite: 2]
        df_year["MVP_Score"] = -1 * (
            (df_year[fip_col] * 0.341) + 
            (df_year[pops_col] * 0.337) + 
            (df_year[whip_col] * 0.322)
        ).round(4)

        # 내림차순 정렬
        df_year = df_year.sort_values(by="MVP_Score", ascending=False).reset_index(drop=True)
        df_year.index = df_year.index + 1

        # 결과 및 비교 대조 출력
        if not df_year.empty:
            model_top = df_year.iloc[0]
            model_winner_name = model_top[name_col]
            model_winner_team = f" ({model_top[team_col]})" if team_col else ""

            st.subheader(f"🔍 {selected_year}시즌 MVP 비교 결과")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.success(f"🤖 **수학적 모델 선정 1위**\n### **{model_winner_name}**{model_winner_team}\n* **MVP 점수**: `{model_top['MVP_Score']}`")

            with col2:
                if actual_mvp_col and not pd.isna(model_top.get(actual_mvp_col)):
                    actual_winner = df_year[df_year[actual_mvp_col].astype(str).str.contains("O|Y|수상|1", na=False)]
                    
                    if not actual_winner.empty:
                        actual_name = actual_winner.iloc[0][name_col]
                        actual_team = f" ({actual_winner.iloc[0][team_col]})" if team_col else ""
                        st.info(f"🏆 **실제 KBO MVP 수상자**\n### **{actual_name}**{actual_team}")
                        
                        if model_winner_name == actual_name:
                            st.balloons()
                            st.success("✅ **일치**: 수학적 모델과 실제 기자단 투표 결과가 일치합니다!")
                        else:
                            st.warning(f"❌ **불일치**: 수학적 1위({model_winner_name})와 실제 수상자({actual_name})가 다릅니다.")
                    else:
                        st.info("🏆 **실제 KBO MVP**: 데이터에 실제 수상자 정보 표시 없음")
                else:
                    st.info("💡 데이터에 `실제MVP` 칼럼이 포함되면 자동 비교 판정이 활성화됩니다.")

            # 전체 리더보드
            st.subheader(f"📊 {selected_year}시즌 전체 투수 리더보드")
            
            show_cols = [name_col]
            if team_col: show_cols.append(team_col)
            if ip_col: show_cols.append(ip_col)
            
            era_col = find_column(df_year, ["평균자책점", "평균자책", "ERA"])
            if era_col: show_cols.append(era_col)
            
            show_cols.extend([fip_col, pops_col, whip_col, "MVP_Score"])
            if actual_mvp_col: show_cols.append(actual_mvp_col)

            st.dataframe(df_year[show_cols], use_container_width=True)

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
