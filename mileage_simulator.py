import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Streamlit 설정
st.set_page_config(page_title="회원 등급제 테스트", layout="wide")

st.title("🧪 회원 등급제 테스트")
st.markdown("""
등급별 **명칭, 기준 금액**, 그리고 **적립률**을 자유롭게 설정하여 시뮬레이션할 수 있습니다.  
GitHub 배포 환경에 맞춰 안정성을 강화한 버전입니다.
""")

@st.cache_data
def load_data():
    # GitHub 배포를 위해 상대 경로 최우선 사용
    file_name = "2026 회원관리.xlsx"
    
    # 1. 현재 실행 스크립트 경로 기준
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path1 = os.path.join(base_dir, file_name)
    # 2. 현재 작업 디렉토리 기준
    path2 = file_name
    # 3. 절대 경로 (로컬용 백업)
    path3 = r'C:\DATASTUDY\FCICB6\data\company\2026 회원관리.xlsx'
    
    df = None
    for path in [path1, path2, path3]:
        if os.path.exists(path):
            try:
                # openpyxl 엔진 명시
                df = pd.read_excel(path, engine='openpyxl')
                break
            except Exception:
                continue
    
    if df is not None:
        try:
            # 필요한 컬럼만 추출 및 이름 정리
            main_df = df.iloc[:, 0:6].copy()
            main_df.columns = ['ID', '이름', '주문금액', '현재등급', '마일리지', '방문횟수']
            return main_df
        except Exception as e:
            st.error(f"데이터 전처리 과정에서 오류가 발생했습니다: {e}")
            return None
    else:
        st.error(f"데이터 파일('{file_name}')을 찾을 수 없습니다. GitHub 레포지토리에 파일이 업로드되었는지 확인해주세요.")
        return None

df = load_data()

if df is not None:
    # 사이드바: 등급별 개인화 설정
    st.sidebar.header("⚙️ 등급별 개인화 설정")

    grade_defaults = ['VVIP', 'VIP', '골드', '실버', '패밀리', '일반']
    threshold_defaults = [10000000, 4000000, 1500000, 500000, 100000, 0]
    rate_defaults = [5.0, 3.0, 2.0, 1.5, 1.0, 0.5]

    settings = []
    for i in range(len(grade_defaults)):
        st.sidebar.markdown(f"**--- {i+1}순위 등급 설정 ---**")
        name = st.sidebar.text_input(f"등급 명칭 {i+1}", value=grade_defaults[i], key=f"n_{i}")
        if i < len(grade_defaults) - 1:
            threshold = st.sidebar.number_input(f"{name} 기준 (원 이상)", value=threshold_defaults[i], step=50000, key=f"t_{i}")
        else:
            threshold = 0 
        rate = st.sidebar.slider(f"{name} 적립률 (%)", 0.0, 10.0, rate_defaults[i], 0.1, key=f"r_{i}")
        settings.append({'등급': name, '기준금액': threshold, '적립률': rate})

    # 등급 판정 로직
    def get_proposed_grade(amount):
        for s in settings:
            if amount >= s['기준금액']:
                return s['등급']
        return settings[-1]['등급']

    df['제안등급'] = df['주문금액'].apply(get_proposed_grade)
    grade_names_custom = [s['등급'] for s in settings]
    rate_map = {s['등급']: s['적립률'] for s in settings}

    # 📋 등급별 요약
    st.divider()
    st.subheader("📋 등급별 요약 (과거 데이터 분석)")

    summary = df.groupby('제안등급').agg({
        '이름': 'count',
        '주문금액': 'sum'
    }).reindex(grade_names_custom)

    summary.columns = ['인원수', '매출 합계']
    summary = summary.reset_index().rename(columns={'제안등급': '등급 명칭'})

    summary['적립률(%)'] = summary['등급 명칭'].map(rate_map)
    # 인당 평균 적립금액
    summary['인당 평균 적립금액'] = ((summary['매출 합계'] / summary['인원수']) * summary['적립률(%)'] / 100).fillna(0).astype(int)
    # 마일리지 총 적립액
    summary['마일리지 총 적립액'] = (summary['매출 합계'] * summary['적립률(%)'] / 100).astype(int)

    # 지표 요약
    total_mileage_hist = summary['마일리지 총 적립액'].sum()
    total_sales_hist = summary['매출 합계'].sum()
    avg_mileage_rate_hist = (total_mileage_hist / total_sales_hist * 100) if total_sales_hist > 0 else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("마일리지 총 적립액", f"{total_mileage_hist:,}원")
    m2.metric("매출 대비 마일리지 적립률", f"{avg_mileage_rate_hist:.2f}%")
    m3.metric("총 분석 회원수", f"{len(df):,}명")

    st.table(summary[['등급 명칭', '인원수', '매출 합계', '적립률(%)', '인당 평균 적립금액', '마일리지 총 적립액']].style.format({
        '인원수': '{:,}명',
        '매출 합계': '{:,}원',
        '적립률(%)': '{:.1f}%',
        '인당 평균 적립금액': '{:,}원',
        '마일리지 총 적립액': '{:,}원'
    }))

    # 🎯 2026년 예상 매출 시뮬레이션
    st.divider()
    st.subheader("🎯 2026년 예상 시뮬레이션")
    target_revenue = st.number_input("2026년 목표 매출액 설정 (원)", value=2_000_000_000, step=100_000_000, key="target_rev")

    sales_share = summary['매출 합계'] / total_sales_hist if total_sales_hist > 0 else 0
    summary['예상 매출'] = (sales_share * target_revenue).astype(int)
    summary['예상 마일리지'] = (summary['예상 매출'] * summary['적립률(%)'] / 100)

    target_total_mileage = int(summary['예상 마일리지'].sum())
    target_avg_rate = (target_total_mileage / target_revenue * 100) if target_revenue > 0 else 0

    p1, p2, p3 = st.columns(3)
    p1.markdown(f"#### 예상 매출 : **{target_revenue:,}원**")
    p2.markdown(f"#### 마일리지 적립금액 : **{target_total_mileage:,}원**")
    p3.markdown(f"#### 마일리지 적립률 : **{target_avg_rate:.2f}%**")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("등급별 인원 비중")
        fig_pie = px.pie(summary, values='인원수', names='등급 명칭', color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        st.subheader("2026 등급별 기대 적립금")
        fig_bar = px.bar(summary, x='등급 명칭', y='예상 마일리지', text_auto=',.0f', color='등급 명칭')
        st.plotly_chart(fig_bar, use_container_width=True)
