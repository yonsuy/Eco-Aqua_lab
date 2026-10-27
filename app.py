import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit.components.v1 as components

# ==========================================
# 1. 페이지 설정 및 디자인 시스템 (CSS)
# ==========================================
st.set_page_config(
    page_title="Eco-Aqua Lab | 하이브리드 수질 정화 시뮬레이터",
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
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .highlight-card {
        background-color: #F5E8E9;
        border: 1px solid #C6535D;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
    }
    h1, h2, h3 {
        color: #7D2638 !important;
        font-weight: 700;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #7D2638;
    }
    .metric-label {
        font-size: 0.8rem;
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

# ==========================================
# 2. 세션 스테이트 초기화 (버튼 연동용)
# ==========================================
if 'exp_logs' not in st.session_state:
    st.session_state.exp_logs = []

if 'process_mode' not in st.session_state:
    st.session_state.process_mode = "CDI + 활성탄 하이브리드"
if 'salinity' not in st.session_state:
    st.session_state.salinity = 3.5
if 'voltage' not in st.session_state:
    st.session_state.voltage = 2.0
if 'initial_conc' not in st.session_state:
    st.session_state.initial_conc = 4.0
if 'mass' not in st.session_state:
    st.session_state.mass = 0.15
if 'cycles' not in st.session_state:
    st.session_state.cycles = 1

# 콜백 함수: 최대 효율성 조건 세팅
def set_max_efficiency():
    st.session_state.process_mode = "CDI + 활성탄 하이브리드"
    st.session_state.salinity = 3.0
    st.session_state.voltage = 2.5
    st.session_state.mass = 0.20
    st.session_state.cycles = 1

# 콜백 함수: 최저 효율성 조건 세팅
def set_min_efficiency():
    st.session_state.process_mode = "활성탄 단독 여과 (AC Only)"
    st.session_state.salinity = 10.0
    st.session_state.voltage = 0.0
    st.session_state.mass = 0.05
    st.session_state.cycles = 10

# ==========================================
# 3. 하이브리드 수학적 연산 모델
# ==========================================
def calculate_hybrid_metrics(process_mode, salinity, voltage, mass, initial_conc, cycles):
    r_ac_only = -0.552 * (salinity**2) - 4.507 * salinity + 98.0
    r_ac_only = np.clip(r_ac_only, 1.0, 98.0)
    
    mass_factor = (mass / 0.1)**0.3
    conc_factor = (4.0 / initial_conc)**0.2
    degradation = 0.92**(cycles - 1)
    
    final_r_ac = np.clip(r_ac_only * mass_factor * conc_factor * degradation, 0.5, 99.5)
    
    if process_mode == "CDI + 활성탄 하이브리드":
        desalination_rate = np.clip((voltage / 3.0) * 85.0 * (salinity / (salinity + 1.0)), 0.0, 90.0)
        eff_salinity = salinity * (1.0 - desalination_rate / 100.0)
        
        r_ac_stage2 = -0.552 * (eff_salinity**2) - 4.507 * eff_salinity + 98.0
        final_r_hybrid = np.clip(r_ac_stage2 * mass_factor * conc_factor * degradation, 0.5, 99.5)
        
        effective_removal = final_r_hybrid
        desal_eff = round(desalination_rate, 1)
    else:
        effective_removal = final_r_ac
        desal_eff = 0.0
        eff_salinity = salinity

    qt = (initial_conc * (effective_removal / 100.0)) / mass
    recovery_rate = np.clip(100.0 * (0.91**(cycles - 1)), 15.0, 100.0)
    
    material_cost = 200 + (mass * 1000)
    energy_cost = (voltage**2 * 120 * cycles) if "CDI" in process_mode else 0
    total_cost = material_cost + energy_cost
    
    cost_per_pct = round(total_cost / max(effective_removal, 0.5), 1)
    
    # 효율성 지수 계산 수식: (제거율^2 / 단위 제거 비용) * 10
    efficiency_index = round(((effective_removal ** 2) / max(cost_per_pct, 1.0)) * 10, 1)
    
    return (
        round(effective_removal, 2), 
        round(qt, 2), 
        round(recovery_rate, 1), 
        int(total_cost), 
        cost_per_pct,
        efficiency_index,
        desal_eff,
        round(eff_salinity, 2),
        round(final_r_ac, 2)
    )

# ==========================================
# 4. 상단 헤더 및 최적/최저 조건 퀵 버튼
# ==========================================
st.title("🧪 Eco-Aqua Lab")
st.caption("고염분 극복을 위한 CDI 탈염 + 활성탄 흡착 하이브리드 수질 정화 가상 시뮬레이터")

# 퀵 컨트롤 버튼 영역
col_btn1, col_btn2, col_col = st.columns([1, 1, 2])
with col_btn1:
    st.button("🚀 최대 효율성 조건 불러오기", on_click=set_max_efficiency, use_container_width=True)
with col_btn2:
    st.button("⚠️ 최저 효율성 조건 불러오기", on_click=set_min_efficiency, use_container_width=True)

st.markdown("---")

# ==========================================
# 5. 사이드바 - 변인 제어 패널 (Session State 연동)
# ==========================================
st.sidebar.header("🎛️ 공정 및 변인 제어 패널")

process_mode = st.sidebar.radio(
    "수질 정화 공정 선택",
    ["활성탄 단독 여과 (AC Only)", "CDI + 활성탄 하이브리드"],
    key='process_mode'
)

st.sidebar.subheader("수질 및 흡착 조건 변인")
salinity = st.sidebar.slider("초기 원수 염분 농도 Salinity (%)", 0.0, 10.0, key='salinity', step=0.1)

if "CDI" in process_mode:
    voltage = st.sidebar.slider("1단계 CDI 인가 전압 Voltage (V)", 0.0, 3.0, key='voltage', step=0.1)
else:
    voltage = 0.0
    st.sidebar.caption("🔒 *활성탄 단독 모드 (CDI 미작동, 0V)*")

initial_conc = st.sidebar.slider("초기 색소 농도 C₀ (g/L)", 1.0, 10.0, key='initial_conc', step=0.5)
mass = st.sidebar.slider("2단계 활성탄 질량 Mass (g)", 0.05, 0.50, key='mass', step=0.01)
cycles = st.sidebar.slider("흡착제 재사용 회차 Reuse Cycles", 1, 10, key='cycles')

(r_eff, qt_val, rec_val, cost_val, cost_per_pct, eff_index, desal_eff, eff_sal, r_ac_comp) = calculate_hybrid_metrics(
    process_mode, salinity, voltage, mass, initial_conc, cycles
)

# ==========================================
# 6. 핵심 KPI 지표 대시보드 (6개 카드)
# ==========================================
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.markdown(f"""
    <div class="highlight-card">
        <div class="metric-label" style="color:#7D2638;">효율성 지수 (Index)</div>
        <div class="metric-value" style="color:#7D2638;">{eff_index}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="lab-card">
        <div class="metric-label">최종 제거율 (R)</div>
        <div class="metric-value">{r_eff}%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="lab-card">
        <div class="metric-label">1단계 탈염율</div>
        <div class="metric-value">{desal_eff}%</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="lab-card">
        <div class="metric-label">단위 제거 비용</div>
        <div class="metric-value">₩{cost_per_pct:,.1f}</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="lab-card">
        <div class="metric-label">총 공정 비용</div>
        <div class="metric-value">₩{cost_val:,}</div>
    </div>
    """, unsafe_allow_html=True)

with col6:
    st.markdown(f"""
    <div class="lab-card">
        <div class="metric-label">단위 흡착량 (Qt)</div>
        <div class="metric-value">{qt_val} <span style="font-size:0.7rem;">mg/g</span></div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 7. 연구 스토리텔링 탭 구성
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🧊 3D 하이브리드 공정 모식도", 
    "🔬 3단계 동적 분광광도계 검증", 
    "📊 공정 효율성 & 경제성 비교", 
    "📋 실험 로그 및 리포트"
])

# ------------------------------------------
# TAB 1: 3D 연속 공정 모식도 (CDI + AC)
# ------------------------------------------
with tab1:
    st.subheader("3D 하이브리드 연속 공정 메커니즘 (CDI 탈염 ➔ 활성탄 흡착)")
    st.markdown(f"<p style='color:#716B6D;'>현재 공정: <b>{process_mode}</b> | 초기 염분: <b>{salinity}%</b> | CDI 전압: <b>{voltage}V</b> | 효율성 지수: <b style='color:#7D2638;'>{eff_index}</b></p>", unsafe_allow_html=True)
    
    is_hybrid = 1 if process_mode == "CDI + 활성탄 하이브리드" else 0
    
    canvas_3d_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 0; background-color: #FFFFFF; display: flex; justify-content: center; align-items: center; height: 390px; overflow: hidden; }}
        canvas {{ border: 1px solid #E7E1DF; border-radius: 8px; background: #FAFAFA; box-shadow: inset 0 0 15px rgba(0,0,0,0.02); }}
    </style>
    </head>
    <body>
    <canvas id="sim3DCanvas" width="820" height="370"></canvas>
    <script>
        const canvas = document.getElementById('sim3DCanvas');
        const ctx = canvas.getContext('2d');
        const isHybrid = {is_hybrid};
        const voltage = {voltage};
        
        let particles = [];
        for(let i=0; i<70; i++) {{
            particles.push({{
                x: Math.random() * 700 + 60,
                y: Math.random() * 220 + 75,
                z: Math.random() * 200 - 100,
                vx: (Math.random() * 0.8) + 0.6,
                vy: (Math.random() - 0.5) * 1.0,
                vz: (Math.random() - 0.5) * 0.6,
                type: Math.random() < 0.5 ? 'dye' : 'salt'
            }});
        }}
        
        function animate() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.strokeStyle = '#E7E1DF'; ctx.setLineDash([5, 5]);
            ctx.beginPath(); ctx.moveTo(410, 20); ctx.lineTo(410, 350); ctx.stroke(); ctx.setLineDash([]);
            
            if(isHybrid) {{
                ctx.fillStyle = '#651D2C'; ctx.fillRect(60, 50, 20, 260);
                ctx.fillStyle = '#1F1D20'; ctx.fillRect(340, 50, 20, 260);
                ctx.fillStyle = '#7D2638'; ctx.font = 'bold 13px sans-serif';
                ctx.fillText('[1단계] CDI 탈염 스택 (' + voltage + 'V)', 110, 35);
                
                ctx.fillStyle = '#E7E1DF'; ctx.fillRect(520, 45, 180, 270);
                ctx.fillStyle = '#29272A'; ctx.fillRect(525, 50, 170, 260);
                ctx.fillStyle = '#7D2638';
                ctx.fillText('[2단계] 활성탄 색소 흡착 필터', 530, 35);
                
                ctx.fillStyle = '#403C42';
                for(let px=545; px<680; px+=30) {{
                    for(let py=75; py<290; py+=35) {{
                        ctx.beginPath(); ctx.arc(px, py, 6, 0, Math.PI*2); ctx.fill();
                    }}
                }}
            }} else {{
                ctx.fillStyle = '#E7E1DF'; ctx.fillRect(260, 45, 300, 270);
                ctx.fillStyle = '#29272A'; ctx.fillRect(265, 50, 290, 260);
                ctx.fillStyle = '#7D2638'; ctx.font = 'bold 14px sans-serif';
                ctx.fillText('활성탄 단독 여과 필터 (이온 경쟁 발생)', 300, 35);
            }}
            
            particles.sort((a, b) => a.z - b.z);
            particles.forEach(p => {{
                if(isHybrid) {{
                    if(p.type === 'salt' && p.x < 380 && voltage > 0) {{
                        let targetY = p.y < 185 ? 60 : 300;
                        p.y += (targetY - p.y) * 0.05 * voltage;
                    }}
                    if(p.type === 'dye' && p.x > 530 && p.x < 680) {{ p.vx *= 0.95; }}
                }} else {{
                    if(p.x > 270 && p.x < 540) {{ p.vx *= 0.98; }}
                }}
                
                p.x += p.vx; p.y += p.vy;
                if(p.x > 800) {{ p.x = 40; p.vx = (Math.random() * 0.8) + 0.6; }}
                if(p.y < 45 || p.y > 325) p.vy *= -1;
                
                let scale = (p.z + 150) / 150;
                ctx.beginPath();
                ctx.arc(p.x, p.y, Math.max(2.5, 5 * scale), 0, Math.PI * 2);
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
    components.html(canvas_3d_html, height=410)

# ------------------------------------------
# TAB 2: 3단계 동적 분광광도계 검증
# ------------------------------------------
with tab2:
    st.subheader("🔬 3단계 동적 분광광도계 스펙트럼 분석 (Pre ➔ Post-CDI ➔ Final-AC)")
    st.markdown("""
    <p style='color:#716B6D;'>
        원수의 정화 전 상태(Pre), 1단계 CDI 탈염 후(Post-CDI), 2단계 활성탄 정화 완료(Final-AC) 
        스펙트럼의 변화를 통해 <b>"CDI 전처리가 활성탄 정화 효율을 어떻게 구원하는지"</b> 직접 확인하세요.
    </p>
    """, unsafe_allow_html=True)
    
    col_spec1, col_spec2 = st.columns([1.3, 1])
    
    with col_spec1:
        wavelengths = np.linspace(380, 900, 100)
        base_peak = 0.2 * initial_conc
        
        abs_pre = base_peak * np.exp(-((wavelengths - 645)/45)**2) + 0.05
        cdi_color_drop = 0.88 if "CDI" in process_mode else 1.0
        abs_cdi = abs_pre * cdi_color_drop
        
        suppression_factor = max(0.04, 1.0 - (r_eff / 100.0) * 0.93)
        abs_final = abs_pre * suppression_factor + np.random.normal(0, 0.004, len(wavelengths))
        
        fig_spec = go.Figure()
        fig_spec.add_trace(go.Scatter(x=wavelengths, y=abs_pre, mode='lines', name='1. 정화 전 (Pre)', line=dict(color='#C6535D', width=3)))
        if "CDI" in process_mode:
            fig_spec.add_trace(go.Scatter(x=wavelengths, y=abs_cdi, mode='lines', name='2. CDI 탈염 후 (Post-CDI)', line=dict(color='#E39A3B', width=2, dash='dot')))
        fig_spec.add_trace(go.Scatter(x=wavelengths, y=abs_final, mode='lines', name='3. 최종 정화 완료 (Final-AC)', line=dict(color='#7D2638', width=2.5, dash='dash')))
        
        fig_spec.update_layout(
            title=f"동적 분광 스펙트럼 ({process_mode}, 초기염분: {salinity}%)",
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
        st.markdown("#### 📐 분광광도계 검증 및 분석 가이드")
        st.markdown(f"""
        <div class="lab-card">
            <p><b>실시간 공정 결과 요약</b></p>
            <ul style='margin-bottom:10px; padding-left:20px; font-size:0.88rem;'>
                <li>초기 원수 염분 농도: <b>{salinity}%</b></li>
                <li>1단계 CDI 탈염 후 잔여 염분: <b>{eff_sal}%</b> ({desal_eff}% 제거)</li>
                <li><b>최종 제거율 (R): <span style="color:#7D2638;">{r_eff}%</span></b> | 효율성 지수: <b style="color:#7D2638;">{eff_index}</b></li>
            </ul>
            <hr style="border:0; border-top:1px solid #E7E1DF; margin:10px 0;">
            <p style="font-size:0.85rem; color:#716B6D;">
                <b>💡 효율성 평가 수식 적용 고찰</b><br>
                제거율과 단위 비용을 동시에 반영한 '효율성 지수'를 통해, 
                전력과 소재 비용이 수반되더라도 고염분에서 고효율을 내는 하이브리드 공정의 경제적 가치를 객관적으로 입증합니다.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("🎯 **비교 팁**: 상단의 **[최대 효율성 조건]** 버튼을 눌러보세요! 최적의 설정값이 자동으로 입력됩니다.")

# ------------------------------------------
# TAB 3: 공정 효율성 & 경제성 비교 차트
# ------------------------------------------
with tab3:
    st.subheader("📊 활성탄 단독 vs CDI 하이브리드 성능 및 효율성 심층 분석")
    c_left, c_right = st.columns(2)
    
    with c_left:
        s_range = np.linspace(0, 10, 50)
        r_ac_curve = np.clip(-0.552 * (s_range**2) - 4.507 * s_range + 98.0, 1.0, 98.0)
        
        desal_curve = np.clip((voltage / 3.0) * 85.0 * (s_range / (s_range + 1.0)), 0.0, 90.0)
        eff_s_curve = s_range * (1.0 - desal_curve / 100.0)
        r_hybrid_curve = np.clip(-0.552 * (eff_s_curve**2) - 4.507 * eff_s_curve + 98.0, 1.0, 99.0)

        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(x=s_range, y=r_ac_curve, mode='lines', name='활성탄 단독 공정', line=dict(color='#716B6D', width=2, dash='dash')))
        fig_comp.add_trace(go.Scatter(x=s_range, y=r_hybrid_curve, mode='lines', name='CDI+AC 하이브리드 공정', line=dict(color='#C6535D', width=3)))
        fig_comp.add_trace(go.Scatter(x=[salinity], y=[r_eff], mode='markers', name='현재 선택 조건', marker=dict(color='#7D2638', size=13, symbol='diamond')))
        
        fig_comp.update_layout(
            title="염분 농도(%) 증가에 따른 공정별 제거율 비교",
            xaxis_title="초기 염분 농도 (%)",
            yaxis_title="색소 제거율 (%)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='#FFFFFF',
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis=dict(range=[0, 105], gridcolor='#E7E1DF'),
            xaxis=dict(gridcolor='#E7E1DF')
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    with c_right:
        v_range = np.linspace(0.1, 3.0, 30)
        index_list = []
        for v in v_range:
            _, _, _, _, _, idx_val, _, _, _ = calculate_hybrid_metrics("CDI + 활성탄 하이브리드", salinity, v, mass, initial_conc, cycles)
            index_list.append(idx_val)
            
        fig_index = go.Figure()
        fig_index.add_trace(go.Scatter(x=v_range, y=index_list, mode='lines+markers', name='효율성 지수', line=dict(color='#963447', width=2.5)))
        fig_index.update_layout(
            title=f"CDI 전압(V)에 따른 효율성 지수 변화 (염분: {salinity}%)",
            xaxis_title="CDI 인가 전압 (V)",
            yaxis_title="효율성 지수 (Score)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='#FFFFFF',
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis=dict(gridcolor='#E7E1DF'),
            xaxis=dict(gridcolor='#E7E1DF')
        )
        st.plotly_chart(fig_index, use_container_width=True)

# ------------------------------------------
# TAB 4: 실험 로그 및 최종 보고서
# ------------------------------------------
with tab4:
    st.subheader("📋 실험 데이터 저장 및 탐구 결과 리포트")
    col_log1, col_log2 = st.columns([1, 2])
    
    with col_log1:
        log_name = st.text_input("실험 조건 명칭", value=f"{process_mode}_{salinity}%_{voltage}V")
        if st.button("📌 현재 조건 데이터 로깅"):
            st.session_state.exp_logs.append({
                "공정명": log_name, 
                "방식": process_mode, 
                "초기염분(%)": salinity, 
                "CDI전압(V)": voltage,
                "CDI탈염율(%)": desal_eff,
                "최종제거율(%)": r_eff, 
                "효율성지수": eff_index,
                "총비용(원)": cost_val, 
                "단위비용(₩/%)": cost_per_pct
            })
            st.success("데이터 로깅 완료!")

    with col_log2:
        if len(st.session_state.exp_logs) > 0:
            df_logs = pd.DataFrame(st.session_state.exp_logs)
            st.dataframe(df_logs, use_container_width=True)
            st.download_button("📥 CSV 데이터 다운로드", df_logs.to_csv(index=False).encode('utf-8-sig'), "hybrid_aqua_lab_results.csv", "text/csv")
        else:
            st.info("기록된 실험 데이터가 없습니다. 좌측 버튼을 눌러 로깅을 시작하세요.")

    st.markdown("---")
    st.markdown(f"""
    ### 📄 [Eco-Aqua Lab] 하이브리드 탐구 최종 요약
    - **적용 공정**: {process_mode} | **원수 염분**: {salinity}% | **CDI 전압**: {voltage}V
    - **효율성 지수**: **{eff_index} 점** (제거율: {r_eff}%, 단위 제거 비용: ₩{cost_per_pct:,.1f}/%)
    - **1단계 탈염 효과**: 염분 농도 **{salinity}% ➔ {eff_sal}%** (탈염율: **{desal_eff}%**)
    - **2단계 정화 효과**: 최종 색소 제거율 **{r_eff}%** (활성탄 단독 시: **{r_ac_comp}%**)
    """)