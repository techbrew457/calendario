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


# Funções de Conversão de Data (DD/MM/AAAA <-> AAAA-MM-DD)
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

# Unidades e Opções Comerciais Fixas
UNIDADES_SALAO = ["Salão Principal", "Salão Master", "Espaço Externo / Quiosque"]
ESTILOS_CHOPP = [
    "Pilsen", "IPA", "Stout", "Bohemian Pilsener", 
    "Premium Golden", "APA", "Vinho", "Red Ale"
]
TAMANHOS_BARRIL = [15, 30, 50]

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
  st.subheader("⚙️ Filtros Globais")
  filtro_unidade_global = st.selectbox("Unidade / Salão", ["Todas"] + UNIDADES_SALAO)
  filtro_mes = st.selectbox(
      "Mês de Referência",
      ["Todos", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
  )

# --- APLICAR FILTROS GLOBAIS ---
eventos_filtrados = reservas
if filtro_unidade_global != "Todas":
  eventos_filtrados = [e for e in eventos_filtrados if e.get("unidade", UNIDADES_SALAO[0]) == filtro_unidade_global]

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
  
  # Soma total de litros de chopp de todos os barris cadastrados
  total_chopp_litros = 0
  for e in eventos_filtrados:
    if e.get("status") != "Cancelado":
      for b in e.get("barris", []):
        total_chopp_litros += int(b.get("litros", 0))

  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Total de Reservas", total_locacoes)
  c2.metric("Confirmados 🟢", confirmados)
  c3.metric("Em Negociação 🟡", pendentes)
  c4.metric("Volume Chopp (L)", f"{total_chopp_litros} L")

  st.divider()

  c5, c6 = st.columns(2)
  c5.metric("Faturamento Projetado", f"R$ {faturamento_projetado:,.2f}")
  c6.metric("Sinais Recebidos (50%)", f"R$ {sinais_recebidos:,.2f}")

  st.divider()
  st.subheader("📈 Histórico Recente de Locações")
  if eventos_filtrados:
    st.dataframe(
        [{
            "Data": formatar_data_br(e.get("date")),
            "Cliente": e.get("cliente"),
            "Salão": e.get("unidade"),
            "Turno": e.get("turno"),
            "Status": e.get("status"),
            "Valor (R$)": f"R$ {float(e.get('valor_locacao', 0)):,.2f}"
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
    unidade_sigla = f"[{ev.get('unidade', 'Salão')[:3]}]"
    
    # Resumo de barris de chopp
    barris = ev.get("barris", [])
    total_litros_ev = sum(int(b.get("litros", 0)) for b in barris)
    chopp_str = f" | 🍺 {total_litros_ev}L" if total_litros_ev > 0 else ""
    
    data_br_cal = formatar_data_br(ev.get("date"))
    titulo = f"{unidade_sigla} {icone} {data_br_cal} - {ev.get('cliente')} ({sinal_txt}){chopp_str}"

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
# 3. NOVA LOCAÇÃO (COM MÚLTIPLOS BARRIS)
# ==========================================
elif menu == "➕ Nova Locação":
  st.title("📝 Registrar Nova Locação ou Negociação")
  st.markdown("Preencha os dados e adicione quantos barris de chopp precisar.")

  with st.form("form_nova_locacao", clear_on_submit=True):
    col_u1, col_u2 = st.columns(2)
    with col_u1:
      unidade_sel = st.selectbox("Unidade / Salão de Festas", UNIDADES_SALAO)
      cliente = st.text_input("Nome do Cliente / Interessado *")
      telefone = st.text_input("WhatsApp do Cliente (Ex: 42999999999)")
      documento = st.text_input("CPF ou CNPJ")
    with col_u2:
      tipo_evento = st.text_input("Tipo de Evento (Ex: Aniversário, Casamento)")
      data_evento = st.date_input("Data do Evento (DD/MM/AAAA)")
      turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite", "Dia Inteiro"])
      qtd_pessoas = st.number_input("Headcount (Pessoas)", min_value=1, value=50, step=1)

    st.divider()
    st.subheader("🍺 Gestão de Múltiplos Barris de Chopp Koch")
    st.markdown("Configure abaixo os barris solicitados para o evento:")

    # Criação de campos para até 4 barris diretamente no formulário
    col_b1, col_b2 = st.columns(2)
    with col_b1:
      st.markdown("**Barril 1**")
      estilo_1 = st.selectbox("Estilo 1", ["Nenhum"] + ESTILOS_CHOPP, key="e1")
      litros_1 = st.selectbox("Tamanho 1", [0, 15, 30, 50], index=2, key="t1") # Padrão 30L

      st.markdown("**Barril 3**")
      estilo_3 = st.selectbox("Estilo 3", ["Nenhum"] + ESTILOS_CHOPP, key="e3")
      litros_3 = st.selectbox("Tamanho 3", [0, 15, 30, 50], index=0, key="t3")

    with col_b2:
      st.markdown("**Barril 2**")
      estilo_2 = st.selectbox("Estilo 2", ["Nenhum"] + ESTILOS_CHOPP, key="e2")
      litros_2 = st.selectbox("Tamanho 2", [0, 15, 30, 50], index=0, key="t2")

      st.markdown("**Barril 4**")
      estilo_4 = st.selectbox("Estilo 4", ["Nenhum"] + ESTILOS_CHOPP, key="e4")
      litros_4 = st.selectbox("Tamanho 4", [0, 15, 30, 50], index=0, key="t4")

    preco_medio_litro = st.number_input("Preço Médio por Litro de Chopp (R$)", min_value=0.0, value=15.0, step=1.0, format="%.2f")

    st.divider()
    st.subheader("💰 Comercial e Valores")
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
      valor_locacao = st.number_input("Valor da Locação (R$)", min_value=0.0, value=1000.0, step=50.0, format="%.2f")
    with col_v2:
      valor_sinal = st.number_input("Sinal 50% (R$)", min_value=0.0, value=500.0, step=50.0, format="%.2f")
    with col_v3:
      valor_caucao = st.number_input("Valor Caução (R$)", min_value=0.0, value=200.0, step=50.0, format="%.2f")

    col_v4, col_v5 = st.columns(2)
    with col_v4:
      status = st.selectbox("Status da Reserva", ["Pendente", "Confirmado", "Cancelado"])
    with col_v5:
      sinal_pago = st.checkbox("50% de Sinal Já Foi Pago?")

    observacoes = st.text_area("Observações Específicas / Acordos")

    submitted = st.form_submit_button("💾 Salvar Nova Locação na Nuvem")
    if submitted:
      if not cliente.strip():
        st.warning("⚠️ O nome do cliente é obrigatório.")
      else:
        # Montar lista de barris ativos
        lista_barris = []
        for est, lit in [(estilo_1, litros_1), (estilo_2, litros_2), (estilo_3, litros_3), (estilo_4, litros_4)]:
          if est != "Nenhum" and lit > 0:
            lista_barris.append({"estilo": est, "litros": int(lit)})

        novo_id = str(int(datetime.now().timestamp()))
        nova_reserva = {
            "id": novo_id,
            "unidade": unidade_sel,
            "cliente": cliente,
            "telefone": telefone,
            "documento": documento,
            "tipo_evento": tipo_evento,
            "date": str(data_evento),
            "turno": turno,
            "qtd_pessoas": int(qtd_pessoas),
            "status": status,
            "sinal_pago": sinal_pago,
            "valor_locacao": float(valor_locacao),
            "valor_sinal": float(valor_sinal),
            "valor_caucao": float(valor_caucao),
            "barris": lista_barris,
            "preco_litro_chopp": float(preco_medio_litro),
            "observacoes": observacoes,
        }
        reservas.append(nova_reserva)
        if salvar_dados_nuvem(reservas):
          st.success("🎉 Locação registrada e salva com sucesso!")
          st.rerun()


# ==========================================
# 4. LISTA & GESTÃO (COM FORMATO DD/MM/AAAA)
# ==========================================
elif menu == "📋 Lista & Gestão":
  st.title("📋 Gerenciamento de Locações")
  st.markdown("Consulte, edite status, abra o WhatsApp direto ou gere esboços de contratos.")

  if eventos_filtrados:
    col_b1, col_b2 = st.columns(2)
    with col_b1:
      filtro_status_lst = st.selectbox("Filtrar por Status", ["Todos", "Confirmado", "Pendente", "Cancelado"])
    with col_b2:
      busca_texto = st.text_input("🔍 Buscar por Cliente", "")

    lista_exibicao = eventos_filtrados
    if filtro_status_lst != "Todos":
      lista_exibicao = [e for e in lista_exibicao if e.get("status") == filtro_status_lst]
    if busca_texto.strip():
      lista_exibicao = [e for e in lista_exibicao if busca_texto.lower() in e.get("cliente", "").lower()]

    for ev in sorted(lista_exibicao, key=lambda x: x["date"]):
      ev_id = ev.get("id")
      st_ev = ev.get("status", "Pendente")
      emoji = "✅" if st_ev == "Confirmado" else ("❌" if st_ev == "Cancelado" else "⏳")
      data_formatada = formatar_data_br(ev.get("date"))

      with st.container(border=True):
        col_i1, col_i2 = st.columns([3, 1])
        with col_i1:
          st.markdown(f"**{emoji} [{ev.get('unidade')}] Data: {data_formatada} - {ev.get('cliente')}**")
          st.caption(f"Turno: **{ev.get('turno')}** | Evento: {ev.get('tipo_evento', 'Geral')} | Status: **{st_ev}**")
          
          # Acesso Direto ao WhatsApp
          tel = ev.get("telefone", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
          if tel:
            st.markdown(f"[💬 Abrir Conversa no WhatsApp](https://wa.me/55{tel})")
          
          v_loc = float(ev.get("valor_locacao", 0))
          
          # Detalhes dos Barris de Chopp
          barris = ev.get("barris", [])
          if not barris and ev.get("qtd_chopp"): # Compatibilidade com registros antigos
            barris = [{"estilo": ev.get("estilo_chopp", "Pilsen"), "litros": ev.get("qtd_chopp")}]
          
          desc_barris = ", ".join([f"{b['litros']}L {b['estilo']}" for b in barris]) if barris else "Nenhum chopp"
          total_litros = sum(int(b.get("litros", 0)) for b in barris)
          v_chopp = total_litros * float(ev.get("preco_litro_chopp", 15.0))

          st.text(f"Locação: R$ {v_loc:,.2f} | Chopp: {desc_barris} (R$ {v_chopp:,.2f})")

        with col_i2:
          btn_edit = st.button("✏️ Editar", key=f"ed_{ev_id}", use_container_width=True)
          btn_contrato = st.button("📄 Contrato", key=f"ct_{ev_id}", use_container_width=True)
          btn_del = st.button("🗑️ Excluir", key=f"dl_{ev_id}", use_container_width=True)

        if btn_del:
          reservas = [r for r in reservas if r.get("id") != ev_id]
          if salvar_dados_nuvem(reservas):
            st.success("Reserva excluída com sucesso!")
            st.rerun()

        # GERAR ESBOÇO DE CONTRATO COM DATA DD/MM/AAAA
        if btn_contrato:
          st.divider()
          st.markdown("### 📄 Esboço de Contrato de Locação")
          
          texto_barris_contrato = "\n".join([f"- {b['litros']} litros de Chopp estilo {b['estilo']}" for b in barris]) if barris else "Nenhum opcional de chopp."

          contrato_texto = f"""
CONTRATO DE LOCAÇÃO TEMPORÁRIA DE SALÃO DE FESTAS
CONTRATANTE: {ev.get('cliente')} | Documento: {ev.get('documento', 'Não informado')} | Tel/WhatsApp: {ev.get('telefone')}
UNIDADE: {ev.get('unidade')}
DATA DO EVENTO: {data_formatada} ({ev.get('turno')})
TIPO DE EVENTO: {ev.get('tipo_evento', 'Festividade')}
HEADCOUNT: {ev.get('qtd_pessoas')} pessoas

CLÁUSULA PRIMEIRA - VALORES E FORMA DE PAGAMENTO:
O valor total ajustado para a locação é de R$ {float(ev.get('valor_locacao', 0)):,.2f}, sendo devido um sinal de 50% no valor de R$ {float(ev.get('valor_sinal', 0)):,.2f}. 
Caução de garantia estipulada em R$ {float(ev.get('valor_caucao', 0)):,.2f}.

CLÁUSULA SEGUNDA - FORNECIMENTO DE CHOPP KOCH:
Opcionais contratados:
{texto_barris_contrato}

CLÁUSULA TERCEIRA - OBSERVAÇÕES:
{ev.get('observacoes', 'Nenhuma observação específica registrada.')}
          """
          st.text_area("Copie o contrato abaixo para enviar ao cliente:", contrato_texto, height=220)

        # PAINEL DE EDIÇÃO RÁPIDA
        if btn_edit:
          st.session_state[f"edit_mode_{ev_id}"] = not st.session_state.get(f"edit_mode_{ev_id}", False)

        if st.session_state.get(f"edit_mode_{ev_id}", False):
          st.divider()
          st.markdown(f"**Editando: {ev.get('cliente')}**")
          
          e_unidade = st.selectbox("Unidade", UNIDADES_SALAO, index=UNIDADES_SALAO.index(ev.get("unidade", UNIDADES_SALAO[0])) if ev.get("unidade") in UNIDADES_SALAO else 0, key=f"u_{ev_id}")
          e_cli = st.text_input("Cliente", value=ev.get("cliente", ""), key=f"c_{ev_id}")
          e_tel = st.text_input("WhatsApp", value=ev.get("telefone", ""), key=f"t_{ev_id}")
          
          try:
            data_obj_atual = datetime.strptime(ev.get("date", "2026-01-01"), "%Y-%m-%d").date()
          except:
            data_obj_atual = datetime.now().date()
          e_data = st.date_input("Data do Evento (DD/MM/AAAA)", value=data_obj_atual, key=f"d_{ev_id}")

          e_stat = st.selectbox("Status", ["Pendente", "Confirmado", "Cancelado"], index=["Pendente", "Confirmado", "Cancelado"].index(ev.get("status", "Pendente")), key=f"s_{ev_id}")
          e_sinal_pago = st.checkbox("Sinal Pago?", value=bool(ev.get("sinal_pago", False)), key=f"sp_{ev_id}")
          e_vloc = st.number_input("Valor Locação", value=float(ev.get("valor_locacao", 0)), step=50.0, key=f"vl_{ev_id}")

          if st.button("💾 Salvar Alterações", key=f"sv_{ev_id}"):
            for item in reservas:
              if item.get("id") == ev_id:
                item["unidade"] = e_unidade
                item["cliente"] = e_cli
                item["telefone"] = e_tel
                item["date"] = str(e_data)
                item["status"] = e_stat
                item["sinal_pago"] = e_sinal_pago
                item["valor_locacao"] = float(e_vloc)
                break
            if salvar_dados_nuvem(reservas):
              st.session_state[f"edit_mode_{ev_id}"] = False
              st.success("Atualizado com sucesso!")
              st.rerun()
  else:
    st.info("Nenhuma locação cadastrada no momento.")
