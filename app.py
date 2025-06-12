# app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Set page configuration for a wider layout
st.set_page_config(layout="wide", page_title="고객 구매 패턴 분석 대시보드")

# --- 1. 데이터 로드 및 캐싱 ---
@st.cache_data
def load_data():
    """
    Kaggle Online Retail Dataset을 로드하고 초기 전처리를 수행합니다.
    데이터 파일은 'Online Retail.xlsx'로 가정하며,
    스크립트와 같은 경로에 있거나 'data/' 폴더 내에 있어야 합니다.
    """
    try:
        df = pd.read_excel("Online Retail.xlsx")
    except FileNotFoundError:
        st.error("데이터 파일을 찾을 수 없습니다. 'Online Retail.xlsx' 파일이 스크립트와 같은 폴더에 있는지 확인해주세요.")
        st.stop() # Stop the app if data is not found

    # 초기 데이터 타입 변환 및 필요한 컬럼명 정리
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df.columns = df.columns.str.strip() # 컬럼명 공백 제거 (안정성)

    return df

# 데이터 로드
df_raw = load_data()
df = df_raw.copy() # 원본 데이터를 보존하기 위해 복사본 사용

# --- 2. 데이터 전처리 ---
# 1. 결측치 처리: CustomerID가 없는 행 제거 (고객별 분석을 위해 필요)
df.dropna(subset=['CustomerID'], inplace=True)
df['CustomerID'] = df['CustomerID'].astype(int) # CustomerID 정수형 변환

# 2. 이상치 및 불필요한 값 제거:
# 수량이 음수이거나 단가가 0 이하인 경우 제거 (반품 또는 불완전한 데이터)
df = df[(df['Quantity'] > 0) & (df['UnitPrice'] > 0)]

# 3. 파생 변수 생성:
df['TotalPrice'] = df['Quantity'] * df['UnitPrice']
df['YearMonth'] = df['InvoiceDate'].dt.to_period('M').astype(str) # 'YYYY-MM' 형식
df['Month'] = df['InvoiceDate'].dt.month # 월 추출
df['DayOfWeek'] = df['InvoiceDate'].dt.day_name() # 요일 이름 추출
df['Hour'] = df['InvoiceDate'].dt.hour # 시간 추출

# 요일 순서 설정 (시각화 시 정렬 위함)
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
df['DayOfWeek'] = pd.Categorical(df['DayOfWeek'], categories=day_order, ordered=True)

# --- 3. Streamlit 웹 애플리케이션 레이아웃 ---
st.title("🛍️ 온라인 소매점 고객 구매 패턴 분석 대시보드")
st.markdown("이 대시보드는 Kaggle 'Online Retail Dataset'을 기반으로 고객 구매 패턴을 분석합니다.")

# 사이드바 필터
st.sidebar.header("데이터 필터")
selected_months = st.sidebar.multiselect(
    "월 선택 (다중 선택 가능)",
    options=sorted(df['Month'].unique()),
    default=sorted(df['Month'].unique())
)

# 선택된 월에 따라 데이터 필터링
if selected_months:
    df_filtered = df[df['Month'].isin(selected_months)]
else:
    df_filtered = df.copy()
    st.sidebar.warning("모든 월이 선택되었습니다. 특정 월을 선택해주세요.")

# 데이터 필터링 결과 확인
if df_filtered.empty:
    st.warning("선택된 필터에 해당하는 데이터가 없습니다. 필터를 조정해주세요.")
    st.stop() # 데이터가 없으면 앱 실행 중지

# --- 4. 핵심 지표 요약 ---
st.subheader("📊 핵심 지표 요약")

total_sales = df_filtered['TotalPrice'].sum()
total_orders = df_filtered['InvoiceNo'].nunique()
total_customers = df_filtered['CustomerID'].nunique()
avg_order_value = total_sales / total_orders if total_orders > 0 else 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("총 매출", f"£{total_sales:,.2f}")
with col2:
    st.metric("총 주문 건수", f"{total_orders:,} 건")
with col3:
    st.metric("총 고객 수", f"{total_customers:,} 명")
with col4:
    st.metric("평균 주문 금액", f"£{avg_order_value:,.2f}")

st.markdown("---")

# --- 5. 주요 시각화 결과 ---

# 5.1 월별 매출 추이
st.subheader("📈 월별 매출 및 주문 건수 추이")
monthly_summary = df_filtered.groupby('YearMonth').agg(
    TotalSales=('TotalPrice', 'sum'),
    OrderCount=('InvoiceNo', 'nunique')
).reset_index().sort_values('YearMonth')

fig_monthly = px.line(
    monthly_summary,
    x='YearMonth',
    y='TotalSales',
    title='월별 총 매출 추이',
    labels={'YearMonth': '연-월', 'TotalSales': '총 매출 (£)'},
    markers=True,
    hover_data={'OrderCount': True}
)
fig_monthly.update_xaxes(type='category')
fig_monthly.update_traces(hovertemplate='<b>%{x}</b><br>총 매출: £%{y:,.2f}<br>주문 건수: %{customdata[0]:,}<extra></extra>')
st.plotly_chart(fig_monthly, use_container_width=True)

fig_order_count = px.bar(
    monthly_summary,
    x='YearMonth',
    y='OrderCount',
    title='월별 주문 건수 추이',
    labels={'YearMonth': '연-월', 'OrderCount': '주문 건수'},
    hover_data={'TotalSales': ':.2f'}
)
fig_order_count.update_xaxes(type='category')
fig_order_count.update_traces(hovertemplate='<b>%{x}</b><br>주문 건수: %{y:,}<br>총 매출: £%{customdata[0]:,.2f}<extra></extra>')
st.plotly_chart(fig_order_count, use_container_width=True)

st.markdown("---")

# 5.2 요일별 / 시간대별 구매 활동
st.subheader("🗓️ 요일별 및 시간대별 구매 활동")

# 요일별 매출
daily_sales = df_filtered.groupby('DayOfWeek')['TotalPrice'].sum().reset_index()
fig_daily = px.bar(
    daily_sales,
    x='DayOfWeek',
    y='TotalPrice',
    title='요일별 총 매출',
    labels={'DayOfWeek': '요일', 'TotalPrice': '총 매출 (£)'},
    category_orders={'DayOfWeek': day_order}
)
st.plotly_chart(fig_daily, use_container_width=True)

# 시간대별 구매 히트맵
hourly_sales = df_filtered.groupby(['DayOfWeek', 'Hour'])['TotalPrice'].sum().unstack(fill_value=0)
fig_heatmap = go.Figure(data=go.Heatmap(
        z=hourly_sales.values,
        x=hourly_sales.columns,
        y=hourly_sales.index,
        colorscale='Viridis'
    ))
fig_heatmap.update_layout(
    title='요일 및 시간대별 총 매출 히트맵',
    xaxis_title='시간',
    yaxis_title='요일'
)
st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown("---")

# 5.3 인기 상품 분석
st.subheader("⭐ 인기 상품 분석")

# 가장 많이 팔린 상품 (수량 기준)
top_selling_products_qty = df_filtered.groupby('Description')['Quantity'].sum().nlargest(10).reset_index()
fig_top_qty = px.bar(
    top_selling_products_qty,
    x='Quantity',
    y='Description',
    orientation='h',
    title='수량 기준 TOP 10 인기 상품',
    labels={'Quantity': '판매 수량', 'Description': '상품명'}
)
fig_top_qty.update_yaxes(categoryorder='total ascending')
st.plotly_chart(fig_top_qty, use_container_width=True)

# 가장 많은 매출을 올린 상품 (금액 기준)
top_revenue_products = df_filtered.groupby('Description')['TotalPrice'].sum().nlargest(10).reset_index()
fig_top_revenue = px.bar(
    top_revenue_products,
    x='TotalPrice',
    y='Description',
    orientation='h',
    title='매출액 기준 TOP 10 인기 상품',
    labels={'TotalPrice': '총 매출액 (£)', 'Description': '상품명'}
)
fig_top_revenue.update_yaxes(categoryorder='total ascending')
st.plotly_chart(fig_top_revenue, use_container_width=True)

st.markdown("---")

# 5.4 국가별 매출 기여도
st.subheader("🌍 국가별 매출 기여도")

country_sales = df_filtered.groupby('Country')['TotalPrice'].sum().reset_index()
# 영국 데이터가 압도적이므로, 파이 차트에서 제외하거나 별도 표시하여 다른 국가들을 더 잘 보이게 할 수 있음
# 여기서는 영국 제외하고 TOP 10 (영국 포함 시 다른 국가들이 너무 작게 보임)
country_sales_top_10 = country_sales.nlargest(11, 'TotalPrice') # 영국 포함 11개
if 'United Kingdom' in country_sales_top_10['Country'].values:
    # 영국이 너무 커서 다른 국가 비중이 적어보이므로, 영국 제외하고 다른 국가들을 보여줌
    country_sales_other = country_sales[country_sales['Country'] != 'United Kingdom']
    fig_country = px.pie(
        country_sales_other,
        values='TotalPrice',
        names='Country',
        title='영국 제외 국가별 매출 기여도',
        hole=0.3 # 도넛 차트
    )
    st.plotly_chart(fig_country, use_container_width=True)
else:
    # 영국이 없으면 그냥 파이차트
    fig_country = px.pie(
        country_sales_top_10,
        values='TotalPrice',
        names='Country',
        title='국가별 매출 기여도 (TOP 10)',
        hole=0.3
    )
    st.plotly_chart(fig_country, use_container_width=True)

st.markdown("---")

st.info("💡 **인사이트:** 본 대시보드를 통해 월별/요일별/시간대별 판매 동향을 파악하고, 인기 상품 및 국가별 매출 기여도를 분석하여 효과적인 마케팅 전략 수립 및 재고 관리에 활용할 수 있습니다.")
