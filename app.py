import base64
from datetime import datetime
import json
import os
import requests
import streamlit as st
from streamlit_calendar import calendar

# --- CONFIGURAÇÃO DA PÁGINA (MOBILE-FIRST) ---
st.set_page_config(
    page_title="Gestão Salão de Festas - Koch Cervejaria",
    page_icon="🍺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS MINIMALISTA E PROFISSIONAL PARA CELULAR E DESKTOP ---
st.markdown(
    """
    <style>
    .fc {
        max-width: 100% !important;
        font-size: 0.85rem !important;
    }
    .fc-toolbar {
        flex-direction: column !important;
        gap: 8px !important;
        align-items: center !important;
    }
    .fc-toolbar-title {
        font-size: 1.1rem !important;
        font-weight: bold;
    }
    .fc-daygrid-day-frame {
        min-height: 75px !important;
    }
    .fc-event {
        font-size: 0.72rem !important;
        padding: 2px 4px !important;
        border-radius: 4px !important;
    }
    div.stButton > button {
        border-radius: 6px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- ARQUITETURA E PERSISTÊNCIA VIA GITHUB ---
ARQUIVO_DADOS = "reservas.json"

try:
  GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
  GITHUB_REPO = st.secrets["GITHUB_REPO"]
  HEADERS = {
      "Authorization": f"token {GITHUB_TOKEN}",
      "Accept": "application/vnd.github.v3+json",
  }
except Exception:
  st.error("⚠️ Erro crítico: As credenciais GITHUB_TOKEN e GITHUB_REPO não foram configuradas nos Secrets do Streamlit.")
  st.stop()


def carregar_dados_nuvem():
  url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ARQUIVO_DADOS}"
  try:
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
      dados_resp = response.json()
      conteudo_bytes = base64.b64decode(dados_resp["content"])
      return json.loads(conteudo_bytes.decode("utf-8")), dados_resp["sha"]
  except Exception:
    pass
  return [], None


def salvar_dados_nuvem(reservas):
  url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ARQUIVO_DADOS}"
  _, sha = carregar_dados_nuvem()
  
  novo_conteudo = json.dumps(reservas, ensure_ascii=False, indent=4)
  conteudo_base64 = base64.b64encode(novo_conteudo.encode("utf-8")).decode("utf-8")

  dados = {
      "message": "Atualização automatizada via Sistema de Gestão de Salão",
      "content": conteudo_base64,
  }
  if sha:
    dados["sha"] = sha

  response = requests.put(url, headers=HEADERS, json=dados)
  if response.status_code not in [200, 201]:
    st.error(f"Erro ao sincronizar com o GitHub: {response.status_code}")
    return False
  return True


# Função para formatar de AAAA-MM-DD para DD/MM/AAAA
def formatar_data_br(data_str):
  try:
    if not data_str:
      return ""
    partes = data_str.split("-")
    if len(partes) == 3:
      return f"{partes[2]}/{partes[1]}/{partes[0]}"
    return data_str
  except Exception:
    return data_str


# Carregar dados em memória
reservas, _ = carregar_dados_nuvem()

# Opções Comerciais Fixas de Estilos de Chopp
ESTILOS_CHOPP = [
    "Pilsen", "IPA", "Stout", "Bohemian Pilsener", 
    "Premium Golden", "APA", "Vinho", "Red Ale"
]

# --- MENU LATERAL (NAVEGAÇÃO E FILTROS) ---
with st.sidebar:
  st.title("🍺 Koch Gestão")
  st.caption("Controle Profissional de Locações")
  st.divider()

  menu = st.radio(
      "Navegação",
      ["📊 Dashboard & Métricas", "📅 Calendário Geral", "➕ Nova Locação", "📋 Lista & Gestão"]
  )

  st.divider()
  st.subheader("⚙️ Filtro Temporal")
  filtro_mes = st.selectbox(
      "Mês de Referência",
      ["Todos", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
  )

# --- APLICAR FILTRO DE MÊS ---
eventos_filtrados = reservas
if filtro_mes != "Todos":
  eventos_filtrados = [e for e in eventos_filtrados if e.get("date", "").split("-")[1] == filtro_mes]


# ==========================================
# 1. DASHBOARD & MÉTRICAS FINANCEIRAS
# ==========================================
if menu == "📊 Dashboard & Métricas":
  st.title("📊 Painel de Controle Consolidado")
  st.markdown("Visão executiva em tempo real do faturamento e ocupação.")

  total_locacoes = len(eventos_filtrados)
  confirmados = sum(1 for e in eventos_filtrados if e.get("status") == "Confirmado")
  pendentes = sum(1 for e in eventos_filtrados if e.get("status") == "Pendente")
  
  faturamento_projetado = sum(float(e.get("valor_locacao", 0)) for e in eventos_filtrados if e.get("status") != "Cancelado")
  sinais_recebidos = sum(float(e.get("valor_sinal", 0)) for e in eventos_filtrados if e.get("sinal_pago", False))
  
  total_chopp_litros = 0
  faturamento_chopp_total = 0.0
  for e in eventos_filtrados:
    if e.get("status") != "Cancelado":
      barris = e.get("barris", [])
      if not barris and e.get("qtd_chopp"):
        total_chopp_litros += int(e.get("qtd_chopp", 0))
        faturamento_chopp_total += int(e.get("qtd_chopp", 0)) * float(e.get("preco_litro_chopp", 15.0))
      else:
        for b in barris:
          total_chopp_litros += int(b.get("litros", 0))
          faturamento_chopp_total += float(b.get("valor_total", 0))

  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Total de Reservas", total_locacoes)
  c2.metric("Confirmados 🟢", confirmados)
  c3.metric("Em Negociação 🟡", pendentes)
  c4.metric("Volume Chopp (L)", f"{total_chopp_litros} L")

  st.divider()

  c5, c6 = st.columns(2)
  c5.metric("Faturamento Salão", f"R$ {faturamento_projetado:,.2f}")
  c6.metric("Sinais Recebidos (Soma)", f"R$ {sinais_recebidos:,.2f}")

  st.divider()
  st.subheader("📈 Histórico Recente de Locações")
  if eventos_filtrados:
    st.dataframe(
        [{
            "Data (DD/MM/AAAA)": formatar_data_br(e.get("date")),
            "Cliente": e.get("cliente"),
            "Turno": e.get("turno"),
            "Status": e.get("status"),
            "Locação (R$)": f"R$ {float(e.get('valor_locacao', 0)):,.2f}"
        } for e in sorted(eventos_filtrados, key=lambda x: x["date"])],
        use_container_width=True
    )
  else:
    st.info("Nenhum dado encontrado para os filtros selecionados.")


# ==========================================
# 2. CALENDÁRIO GERAL
# ==========================================
elif menu == "📅 Calendário Geral":
  st.title("📆 Calendário Interativo de Locações")
  st.markdown("🟢 **Verde**: Confirmado/Locado | 🟡 **Amarelo**: Em Negociação | 🔴 **Vermelho**: Cancelado")

  calendar_events = []
  for ev in eventos_filtrados:
    st_ev = ev.get("status", "Pendente")
    if st_ev == "Confirmado":
      cor, icone = "#28a745", "✅ [Locado]"
    elif st_ev == "Cancelado":
      cor, icone = "#dc3545", "❌ [Cancel.]"
    else:
      cor, icone = "#ffc107", "⏳ [Negoc.]"

    sinal_txt = "Sinal OK" if ev.get("sinal_pago") else "Sinal Pendente"
    
    barris = ev.get("barris", [])
    total_litros_ev = sum(int(b.get("litros", 0)) for b in barris)
    chopp_str = f" | 🍺 {total_litros_ev}L" if total_litros_ev > 0 else ""
    
    data_br_cal = formatar_data_br(ev.get("date"))
    titulo = f"{icone} {data_br_cal} - {ev.get('cliente')} ({sinal_txt}){chopp_str}"

    calendar_events.append({
        "title": titulo,
        "start": ev.get("date"),
        "allDay": True,
        "backgroundColor": cor,
        "borderColor": cor,
    })

  calendar_options = {
      "headerToolbar": {"left": "prev,next", "center": "title", "right": "today"},
      "initialView": "dayGridMonth",
      "locale": "pt-br",
  }

  calendar(events=calendar_events, options=calendar_options, key="calendario_principal")


# ==========================================
# 3. NOVA LOCAÇÃO
# ==========================================
elif menu == "➕ Nova Locação":
  st.title("📝 Registrar Nova Locação ou Negociação")
  st.markdown("Preencha os dados, opcionais de som, monitor/cuidador, barris e valores.")

  with st.form("form_nova_locacao", clear_on_submit=True):
    col_u1, col_u2 = st.columns(2)
    with col_u1:
      cliente = st.text_input("Nome do Cliente / Interessado *")
      telefone = st.text_input("WhatsApp do Cliente (Ex: 42999999999)")
      documento = st.text_input("CPF ou CNPJ")
    with col_u2:
      tipo_evento = st.text_input("Tipo de Evento (Ex: Aniversário, Casamento)")
      
      st.markdown("**Data do Evento**")
      col_d1, col_d2, col_d3 = st.columns(3)
      hoje = datetime.now()
      with col_d1:
        dia_ev = st.selectbox("Dia", list(range(1, 32)), index=hoje.day - 1, key="d_dia")
      with col_d2:
        mes_ev = st.selectbox("Mês", list(range(1, 13)), index=hoje.month - 1, key="d_mes", format_func=lambda x: f"{x:02d}")
      with col_d3:
        ano_ev = st.selectbox("Ano", [hoje.year, hoje.year + 1, hoje.year + 2], index=0, key="d_ano")

      turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite", "Dia Inteiro"])
      qtd_pessoas = st.number_input("Headcount (Pessoas)", min_value=1, value=50, step=1)

    st.divider()
    st.subheader("🔊 Opcionais e Serviços Adicionais")
    
    col_op1, col_op2 = st.columns(2)
    with col_op1:
      valor_som = st.number_input("Aluguel da Caixa de Som (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f")
    with col_op2:
      taxa_cuidador_str = st.selectbox("Taxa de Monitor / Cuidador para a festa?", ["Não", "Sim"])
      taxa_cuidador = True if taxa_cuidador_str == "Sim" else False

    st.divider()
    st.subheader("🍺 Gestão de Múltiplos Barris de Chopp Koch")
    st.markdown("Defina o estilo, tamanho e o **valor específico** para cada barril:")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
      st.markdown("##### 🛢️ Barril 1")
      estilo_1 = st.selectbox("Estilo 1", ["Nenhum"] + ESTILOS_CHOPP, key="e1")
      litros_1 = st.selectbox("Tamanho 1", [0, 15, 30, 50], index=2, key="t1")
      valor_b1 = st.number_input("Valor do Barril 1 (R$)", min_value=0.0, value=300.0, step=10.0, format="%.2f", key="vb1")

      st.markdown("##### 🛢️ Barril 3")
      estilo_3 = st.selectbox("Estilo 3", ["Nenhum"] + ESTILOS_CHOPP, key="e3")
      litros_3 = st.selectbox("Tamanho 3", [0, 15, 30, 50], index=0, key="t3")
      valor_b3 = st.number_input("Valor do Barril 3 (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="vb3")

    with col_b2:
      st.markdown("##### 🛢️️ Barril 2")
      estilo_2 = st.selectbox("Estilo 2", ["Nenhum"] + ESTILOS_CHOPP, key="e2")
      litros_2 = st.selectbox("Tamanho 2", [0, 15, 30, 50], index=0, key="t2")
      valor_b2 = st.number_input("Valor do Barril 2 (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="vb2")

      st.markdown("##### 🛢️ Barril 4")
      estilo_4 = st.selectbox("Estilo 4", ["Nenhum"] + ESTILOS_CHOPP, key="e4")
      litros_4 = st.selectbox("Tamanho 4", [0, 15, 30, 50], index=0, key="t4")
      valor_b4 = st.number_input("Valor do Barril 4 (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="vb4")

    st.divider()
    st.subheader("💰 Comercial e Valores do Salão")
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
      valor_locacao = st.number_input("Valor da Locação (R$)", min_value=0.0, value=1000.0, step=50.0, format="%.2f")
    with col_v2:
      valor_sinal = st.number_input("Valor do Sinal (R$)", min_value=0.0, value=500.0, step=50.0, format="%.2f")
    with col_v3:
      valor_caucao = st.number_input("Valor Caução (R$)", min_value=0.0, value=200.0, step=50.0, format="%.2f")

    col_v4, col_v5 = st.columns(2)
    with col_v4:
      status = st.selectbox("Status da Reserva", ["Pendente", "Confirmado", "Cancelado"])
    with col_v5:
      sinal_pago = st.checkbox("Sinal Já Foi Pago?")

    observacoes = st.text_area("Observações Específicas / Acordos")

    submitted = st.form_submit_button("💾 Salvar Nova Locação na Nuvem")
    if submitted:
      if not cliente.strip():
        st.warning("⚠️ O nome do cliente é obrigatório.")
      else:
        try:
          data_formatada_str = f"{ano_ev}-{int(mes_ev):02d}-{int(dia_ev
