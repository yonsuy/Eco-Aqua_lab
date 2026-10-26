import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit.components.v1 as components

# ==========================================
# 1. 페이지 설정 및 디자인 시스템 (CSS)
# ==========================================
st.set_page_config(
    page_title="Eco-Aqua Lab | 수질 정화 시뮬레이터",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #F7F5F2;
        color: #29272A;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E7E1DF;
    }
    .lab-card {
        background-color: #FFFFFF;
        border: 1px solid #E7E1DF;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .highlight-card {
        background-color: #F5E8E9;
        border: 1px solid #C6535D;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 16px;
    }
    h1, h2, h3 {
        color: #7D2638 !important;
        font-weight: 700;
    }
    .metric-value {
        font-size: 1.7rem;
        font-weight: 700;
        color: #7D2638;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #716B6D;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stButton>button {
        background-color: #963447;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #7D2638;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

if 'exp_logs' not in st.session_state:
    st.session_state.exp_logs = []

# ==========================================
# 2. 수학적 모델링 및 계산 함수
# ==========================================
def calculate_metrics(mode, salinity, voltage, mass, initial_conc, cycles):
    r_base = -0.552 * (salinity**2) - 4.507 * salinity + 98.0
    r_base = np.clip(r_base, 1.0, 98.0)
    
    if mode == "CDI 전기흡착 스택":
        vol_boost = (voltage / 3.0) * 65.0 * (salinity / (salinity + 2.0))
        calc_removal = r_base + vol_boost
    else:
        calc_removal = r_base
        
    mass_factor = (mass / 0.1)**0.3
    conc_factor = (4.0 / initial_conc)**0.2
    degradation = 0.92**(cycles - 1)
    
    final_removal = np.clip(calc_removal * mass_factor * conc_factor * degradation, 0.5, 99.5)
    qt = (initial_conc * (final_removal / 100.0)) / mass
    recovery_rate = np.clip(100.0 * (0.91**(cycles - 1)), 15.0, 100.0)
    
    material_cost = 200 + (mass * 1000)
    energy_cost = (voltage**2 * 120 * cycles) if mode == "CDI 전기흡착 스택" else 0
    total_cost = material_cost + energy_cost
    
    cost_per_percent = round(total_cost / max(final_removal, 0.5), 1)
    
    return round(final_removal, 2), round(qt, 2), round(recovery_rate, 1), int(total_cost), cost_per_percent

# ==========================================
# 3. 상단 헤더
# ==========================================
st.title("🧪 Eco-Aqua Lab")
st.caption("염분 및 CDI 전기흡착 기반 스마트 수질 정화 가상 시뮬레이터 | Research Data Dashboard")
st.markdown("---")

# ==========================================
# 4. 사이드바 - 실험 변수 제어 패널
# ==========================================
st.sidebar.header("🎛️ 실험 변수 제어 패널")

mode = st.sidebar.radio(
    "정화 공정 방식 선택",
    ["활성탄 여과 (기본)", "CDI 전기흡착 스택"]
)

st.sidebar.subheader("수질 및 소재 파라미터")
salinity = st.sidebar.slider("염분 농도 Salinity (%)", 0.0, 10.0, 3.5, 0.1)

if mode == "CDI 전기흡착 스택":
    voltage = st.sidebar.slider("CDI 인가 전압 Voltage (V)", 0.0, 3.0, 1.5, 0.1)
else:
    voltage = 0.0
    st.sidebar.caption("🔒 *활성탄 단독 모드 (0V)*")

initial_conc = st.sidebar.slider("초기 색소 농도 C₀ (g/L)", 1.0, 10.0, 4.0, 0.5)
mass = st.sidebar.slider("흡착제 질량 Mass (g)", 0.05, 0.50, 0.10, 0.01)
cycles = st.sidebar.slider("흡착제 재사용 회차 Reuse Cycles", 1, 10, 1)

r_eff, qt_val, rec_val, cost_val, cost_per_pct = calculate_metrics(mode, salinity, voltage, mass, initial_conc, cycles)

# ==========================================
# 5. 핵심 지표 KPI 카드
# ==========================================
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="lab-card">
        <div class="metric-label">색소 제거율 (R)</div>
        <div class="metric-value">{r_eff}%</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="lab-card">
        <div class="metric-label">흡착 용량 (Qt)</div>
        <div class="metric-value">{qt_val} <span style="font-size:0.9rem;">mg/g</span></div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="lab-card">
        <div class="metric-label">성능 회복률 (Rec)</div>
        <div class="metric-value">{rec_val}%</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="lab-card">
        <div class="metric-label">총 공정 비용</div>
        <div class="metric-value">₩{cost_val:,}</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="highlight-card">
        <div class="metric-label" style="color:#7D2638;">단위 제거 비용 (₩/%)</div>
        <div class="metric-value" style="color:#7D2638;">₩{cost_per_pct:,.1f}</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 6. 연구 스토리텔링 순서에 따른 탭 재배치
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🧊 3D 입체 공정 모식도", 
    "🔬 실시간 동적 분광광도계 검증", 
    "📊 데이터 분석 차트", 
    "📋 실험 로그 및 보고서"
])

with tab1:
    st.subheader("3D 원근감 기반 전기흡착 및 이온 포집 공정 모식도")
    st.markdown(f"<p style='color:#716B6D;'>현재 공정: <b>{mode}</b> | 염분 농도: <b>{salinity}%</b> | 전압: <b>{voltage}V</b></p>", unsafe_allow_html=True)
    
    is_cdi = 1 if mode == "CDI 전기흡착 스택" else 0
    
    canvas_3d_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 0; background-color: #FFFFFF; display: flex; justify-content: center; align-items: center; height: 400px; overflow: hidden; }}
        canvas {{ border: 1px solid #E7E1DF; border-radius: 8px; background: #FAFAFA; box-shadow: inset 0 0 15px rgba(0,0,0,0.02); }}
    </style>
    </head>
    <body>
    <canvas id="sim3DCanvas" width="800" height="380"></canvas>
    <script>
        const canvas = document.getElementById('sim3DCanvas');
        const ctx = canvas.getContext('2d');
        const isCdi = {is_cdi};
        const voltage = {voltage};
        
        let particles = [];
        for(let i=0; i<65; i++) {{
            particles.push({{
                x: Math.random() * 600 + 100,
                y: Math.random() * 220 + 80,
                z: Math.random() * 200 - 100,
                vx: (Math.random() - 0.5) * 1.3,
                vy: (Math.random() - 0.5) * 1.3,
                vz: (Math.random() - 0.5) * 0.8,
                type: Math.random() < 0.55 ? 'dye' : 'salt',
                radius: Math.random() * 3 + 4
            }});
        }}
        
        function animate() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            if(isCdi) {{
                ctx.fillStyle = '#651D2C'; ctx.fillRect(120, 60, 30, 260);
                ctx.fillStyle = '#8B2C3D'; ctx.fillRect(150, 45, 20, 260);
                ctx.fillStyle = '#1F1D20'; ctx.fillRect(630, 60, 30, 260);
                ctx.fillStyle = '#403C42'; ctx.fillRect(660, 45, 20, 260);
                ctx.fillStyle = '#7D2638'; ctx.font = 'bold 13px sans-serif';
                ctx.fillText('(+) 양극 (Cl⁻ 이온 포집)', 110, 30);
                ctx.fillText('(-) 음극 (Na⁺ 이온 포집)', 620, 30);
                ctx.strokeStyle = 'rgba(198, 83, 93, 0.3)'; ctx.lineWidth = 1.5;
                for(let ly = 90; ly <= 290; ly += 50) {{
                    ctx.beginPath(); ctx.moveTo(170, ly); ctx.lineTo(630, ly); ctx.stroke();
                }}
            }} else {{
                ctx.fillStyle = '#E7E1DF'; ctx.fillRect(315, 45, 170, 300);
                ctx.fillStyle = '#29272A'; ctx.fillRect(320, 50, 160, 290);
                ctx.fillStyle = '#403C42';
                for(let px=340; px<460; px+=30) {{
                    for(let py=80; py<300; py+=40) {{
                        ctx.beginPath(); ctx.arc(px, py, 7, 0, Math.PI*2); ctx.fill();
                    }}
                }}
                ctx.fillStyle = '#7D2638'; ctx.font = 'bold 13px sans-serif';
                ctx.fillText('3D 활성탄 다공성 미세 필터 단면', 305, 30);
            }}
            
            particles.sort((a, b) => a.z - b.z);
            particles.forEach(p => {{
                if(isCdi && p.type === 'salt') {{
                    let targetX = p.y < 200 ? 135 : 645;
                    p.x += (targetX - p.x) * (0.008 * (voltage + 0.5));
                }}
                p.x += p.vx; p.y += p.vy; p.z += p.vz;
                if(p.x < 90 || p.x > 710) p.vx *= -1;
                if(p.y < 50 || p.y > 330) p.vy *= -1;
                if(p.z < -100 || p.z > 100) p.vz *= -1;
                
                let scale = (p.z + 150) / 150;
                ctx.beginPath();
                ctx.arc(p.x, p.y, Math.max(2, p.radius * scale), 0, Math.PI * 2);
                ctx.fillStyle = (p.type === 'dye') ? '#C6535D' : '#8C8588';
                ctx.globalAlpha = 0.85; ctx.fill();
                ctx.lineWidth = 1; ctx.strokeStyle = '#FFFFFF'; ctx.stroke();
                ctx.globalAlpha = 1.0; ctx.closePath();
            }});
            requestAnimationFrame(animate);
        }}
        animate();
    </script>
    </body>
    </html>
    """
    components.html(canvas_3d_html, height=420)

with tab2:
    st.subheader("실시간 동적 분광광도계 스펙트럼 분석 및 이론 검증")
    st.markdown("""
    <p style='color:#716B6D;'>
        사이드바에서 설정하신 실험 변수에 반응하여 분광광도계 흡광도 곡선(Pre vs Post)이 실시간으로 자동 연산·출력됩니다.
    </p>
    """, unsafe_allow_html=True)
    
    col_spec1, col_spec2 = st.columns([1.3, 1])
    
    with col_spec1:
        wavelengths = np.linspace(380, 900, 100)
        base_peak = 0.2 * initial_conc
        
        abs_pre = base_peak * np.exp(-((wavelengths - 645)/45)**2) + 0.05
        suppression_factor = max(0.05, 1.0 - (r_eff / 100.0) * 0.92)
        abs_post = abs_pre * suppression_factor + np.random.normal(0, 0.005, len(wavelengths))
        
        fig_spec = go.Figure()
        fig_spec.add_trace(go.Scatter(x=wavelengths, y=abs_pre, mode='lines', name='정화 전 (Pre)', line=dict(color='#C6535D', width=3)))
        fig_spec.add_trace(go.Scatter(x=wavelengths, y=abs_post, mode='lines', name='정화 후 (Post)', line=dict(color='#7D2638', width=2.5, dash='dash')))
        fig_spec.update_layout(
            title=f"동적 분광 스펙트럼 시뮬레이션 ({mode}, 염분: {salinity}%, 전압: {voltage}V)",
            xaxis_title="파장 (nm)",
            yaxis_title="흡광도 (Absorbance)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='#FFFFFF',
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis=dict(gridcolor='#E7E1DF'),
            xaxis=dict(gridcolor='#E7E1DF')
        )
        st.plotly_chart(fig_spec, use_container_width=True)

    with col_spec2:
        st.markdown("#### 흡광도 분석 및 이론 공식 참고")
        st.markdown(f"""
        <div class="lab-card">
            <p><b>현재 적용된 상태 요약</b></p>
            <ul style='margin-bottom:10px; padding-left:20px; font-size:0.9rem;'>
                <li>공정: <b>{mode}</b></li>
                <li>염분 농도: <b>{salinity}%</b></li>
                <li>연산된 제거율 (R): <span style="color:#7D2638; font-weight:bold;">{r_eff}%</span></li>
            </ul>
            <hr style="border:0; border-top:1px solid #E7E1DF; margin:10px 0;">
            <p style="font-size:0.85rem; color:#716B6D;">
                <b>람베르트-베르 법칙 (Beer-Lambert Law)</b><br>
                흡광도는 용질의 농도에 비례합니다 (A = ε b C). 
                정화 과정 전후의 최대 흡수 파장(약 645 nm)에서의 흡광도 감소율을 통해 실제 제거율을 정량 산출합니다.
            </p>
            <p style="font-size:0.85rem; color:#716B6D; margin-top:8px;">
                <b>정화 효율 산출 공식:</b><br>
                R (%) = (1 - A_post / A_pre) * 100
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("🎯 **시뮬레이션 검증**: 사이드바에서 염분을 0%에서 8%로 높여보세요. 보라색선(정화 후)이 빨간색선과 밀착하며 **이온 경쟁으로 인한 정화 저하 현상**이 실시간 스펙트럼으로 시각화됩니다!")

with tab3:
    st.subheader("실시간 수처리 성능 및 경제성 그래프")
    c_left, c_right = st.columns(2)
    
    with c_left:
        time_pts = np.linspace(0, 60, 50)
        k_rate = 0.08 if mode == "CDI 전기흡착 스택" else 0.05
        r_time = r_eff * (1 - np.exp(-k_rate * time_pts))
        
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=time_pts, y=r_time, mode='lines', name='제거율 (R)', line=dict(color='#7D2638', width=3)))
        fig1.update_layout(title="시간 경과에 따른 색소 제거율", xaxis_title="처리 시간 (분)", yaxis_title="제거율 (%)", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#FFFFFF', margin=dict(l=20, r=20, t=40, b=20), yaxis=dict(range=[0, 105], gridcolor='#E7E1DF'), xaxis=dict(gridcolor='#E7E1DF'))
        st.plotly_chart(fig1, use_container_width=True)

    with c_right:
        s_range = np.linspace(0, 10, 50)
        r_ac_curve = np.clip(-0.552 * (s_range**2) - 4.507 * s_range + 98.0, 1.0, 98.0)
        r_cdi_curve = np.clip(r_ac_curve + ((1.5 / 3.0) * 65.0 * (s_range / (s_range + 2.0))), 1.0, 99.0)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=s_range, y=r_ac_curve, mode='lines', name='활성탄 여과', line=dict(color='#716B6D', width=2, dash='dash')))
        fig2.add_trace(go.Scatter(x=s_range, y=r_cdi_curve, mode='lines', name='CDI 전기흡착', line=dict(color='#C6535D', width=3)))
        fig2.add_trace(go.Scatter(x=[salinity], y=[r_eff], mode='markers', name='현재 조건', marker=dict(color='#7D2638', size=12, symbol='diamond')))
        fig2.update_layout(title="염분 농도(%)에 따른 정화 효율 비교", xaxis_title="염분 농도 (%)", yaxis_title="제거율 (%)", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#FFFFFF', margin=dict(l=20, r=20, t=40, b=20), yaxis=dict(range=[0, 105], gridcolor='#E7E1DF'), xaxis=dict(gridcolor='#E7E1DF'))
        st.plotly_chart(fig2, use_container_width=True)

with tab4:
    st.subheader("실험 결과 데이터 기록 및 연구 보고서")
    col_log1, col_log2 = st.columns([1, 2])
    
    with col_log1:
        log_name = st.text_input("실험 조건 명칭", value=f"{mode}_{salinity}%_{cycles}회차")
        if st.button("📌 현재 데이터 로깅"):
            st.session_state.exp_logs.append({
                "조건명": log_name, "공정": mode, "염분(%)": salinity, "전압(V)": voltage,
                "질량(g)": mass, "회차(회)": cycles, "제거율(%)": r_eff, "Qt(mg/g)": qt_val, "비용(원)": cost_val, "단위비용(₩/%)": cost_per_pct
            })
            st.success("기록 완료!")

    with col_log2:
        if len(st.session_state.exp_logs) > 0:
            df_logs = pd.DataFrame(st.session_state.exp_logs)
            st.dataframe(df_logs, use_container_width=True)
            st.download_button("📥 CSV 다운로드", df_logs.to_csv(index=False).encode('utf-8-sig'), "eco_aqua_lab_results.csv", "text/csv")
        else:
            st.info("기록된 데이터가 없습니다.")

    st.markdown("---")
    st.markdown(f"""
    ### 📄 [Eco-Aqua Lab] 종합 연구 요약
    - **공정 방식**: {mode} | **염분**: {salinity}% | **전압**: {voltage}V
    - **색소 제거율**: **{r_eff}%** | **단위 흡착량**: **{qt_val} mg/g** | **1% 제거당 비용**: **₩{cost_per_pct:,.1f} / %**
    """)