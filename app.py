import base64
from datetime import datetime, time
import json
import os
import requests
import streamlit as st
from streamlit_calendar import calendar

# Configuração da página para ocupar a tela inteira (ótimo para celular)
st.set_page_config(
    page_title="Reservas Espaço - Koch Cervejaria", page_icon="🍺", layout="wide"
)

# --- CSS PERSONALIZADO PARA OTIMIZAR O CALENDÁRIO NO CELULAR ---
st.markdown(
    """
    <style>
    /* Força o calendário a ocupar 100% da largura e se adaptar a telas pequenas */
    .fc {
        max-width: 100% !important;
        font-size: 0.8rem !important;
    }
    
    /* Ajusta o cabeçalho do calendário para não quebrar em telas estreitas */
    .fc-toolbar {
        flex-direction: column !important;
        gap: 10px !important;
        align-items: center !important;
    }
    
    .fc-toolbar-title {
        font-size: 1.1rem !important;
    }

    /* Deixa os dias do mês com uma altura confortável para toque no celular */
    .fc-daygrid-day-frame {
        min-height: 70px !important;
    }

    /* Ajusta o texto dos eventos dentro dos quadradinhos */
    .fc-event {
        font-size: 0.7rem !important;
        padding: 1px 3px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Arquivo JSON para salvar as reservas permanentemente no GitHub
ARQUIVO_DADOS = "reservas.json"

# Configurações do GitHub obtidas dos Streamlit Secrets
try:
  GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
  GITHUB_REPO = st.secrets["GITHUB_REPO"]
  ARQUIVO_CAMINHO = ARQUIVO_DADOS
  HEADERS = {
      "Authorization": f"token {GITHUB_TOKEN}",
      "Accept": "application/vnd.github.v3+json",
  }
except Exception as e:
  st.error(
      "Erro: As credenciais do GitHub (GITHUB_TOKEN e GITHUB_REPO) não foram encontradas nos Secrets do Streamlit."
  )
  st.stop()


def carregar_reservas():
  url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ARQUIVO_CAMINHO}"
  response = requests.get(url, headers=HEADERS)
  if response.status_code == 200:
    dados_resp = response.json()
    conteudo_base64 = dados_resp["content"]
    conteudo_bytes = base64.b64decode(conteudo_base64)
    return json.loads(conteudo_bytes.decode("utf-8")), dados_resp["sha"]
  return [], None


def salvar_no_github(reservas):
  url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ARQUIVO_CAMINHO}"
  _, sha = carregar_reservas()

  novo_conteudo = json.dumps(reservas, ensure_ascii=False, indent=4)
  conteudo_base64 = base64.b64encode(novo_conteudo.encode("utf-8")).decode("utf-8")

  dados = {
      "message": "Atualização de reservas via app do salão",
      "content": conteudo_base64,
  }
  if sha:
    dados["sha"] = sha

  response = requests.put(url, headers=HEADERS, json=dados)
  if response.status_code not in [200, 201]:
    st.error(
        f"Erro ao salvar no GitHub ({response.status_code}): {response.json().get('message', 'Erro desconhecido')}"
    )
    return False
  return True


# Função auxiliar para formatar a data de AAAA-MM-DD para DD/MM/AAAA
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


# Carrega as reservas da nuvem
reservas, _ = carregar_reservas()

# --- MENU LATERAL: LOGO, TÍTULO E NAVEGAÇÃO ---
with st.sidebar:
  if os.path.exists("logo.png"):
    st.image("logo.png", use_container_width=True)
  
  st.title("Reservas Espaço")
  st.divider()
  
  menu = st.radio("Navegação", ["📅 Painel / Calendário", "➕ Nova Locação"])

  st.divider()
  st.subheader("🔍 Filtros Globais")
  filtro_mes = st.selectbox(
      "Filtrar por Mês",
      ["Todos", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"],
  )

st.title("🍻 Reservas Espaço - Koch Cervejaria")

# Lista oficial atualizada de estilos de chopp da cervejaria
ESTILOS_CHOPP = [
    "Pilsen",
    "IPA",
    "Stout",
    "Bohemian Pilsener",
    "Premium Golden",
    "APA",
    "Vinho",
    "Red Ale",
    "Nenhum",
]

# Filtragem de eventos por mês
eventos_filtrados = reservas
if filtro_mes != "Todos":
  eventos_filtrados = [
      e for e in reservas if e.get("date", "").split("-")[1] == filtro_mes
  ]

if menu == "➕ Nova Locação":
  st.subheader("📝 Registrar Nova Locação / Negociação")
  with st.form("form_cadastro", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
      cliente = st.text_input("Nome do Cliente / Interessado")
      telefone = st.text_input("Telefone / WhatsApp (Ex: 42999999999)")
      tipo_evento = st.text_input("Tipo de Evento (Ex: Aniversário, Confraternização...)")
      data_evento = st.date_input("Data da Locação")
    with col2:
      turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite", "Dia Inteiro"])
      qtd_pessoas = st.number_input("Headcount (Qtd de Pessoas)", min_value=1, value=50, step=1)
      status = st.selectbox("Status da Locação", ["Confirmado", "Pendente", "Cancelado"])
      sinal_pago = st.checkbox("50% de Sinal Pago?")

    st.divider()
    st.subheader("💰 Valores e Custos")
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
      valor_locacao = st.number_input("Valor da Locação (R$)", min_value=0.0, value=0.0, step=50.0, format="%.2f")
    with col_v2:
      sugerido_sinal = valor_locacao / 2.0
      valor_sinal = st.number_input("Valor do Sinal - 50% (R$)", min_value=0.0, value=sugerido_sinal, step=50.0, format="%.2f")
    with col_v3:
      valor_caucao = st.number_input("Valor da Caução (R$)", min_value=0.0, value=0.0, step=50.0, format="%.2f")

    col_v4, col_v5 = st.columns(2)
    with col_v4:
      taxa_extra = st.number_input("Taxa Extra (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f")
    with col_v5:
      aluguel_som = st.number_input("Aluguel de Som (R$)", min_value=0.0, value=0.0, step=50.0, format="%.2f")

    st.divider()
    st.subheader("🍺 Opcionais de Chopp & Observações")
    col3, col4, col5 = st.columns(3)
    with col3:
      qtd_chopp = st.number_input("Volume de Chopp (Litros)", min_value=0, value=0, step=10)
    with col4:
      preco_litro_chopp = st.number_input("Preço do Litro (R$)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
    with col5:
      estilo_chopp = st.selectbox("Estilo do Chopp", ESTILOS_CHOPP)

    observacoes = st.text_area("Observações Gerais (Ex: Segunda opção para o dia)")

    submitted = st.form_submit_button("Salvar Locação no Sistema")
    if submitted:
      if not cliente.strip():
        st.warning("Por favor, preencha o nome do cliente.")
      else:
        novo_id = str(int(datetime.now().timestamp()))

        nova_reserva = {
            "id": novo_id,
            "cliente": cliente,
            "telefone": telefone,
            "tipo_evento": tipo_evento,
            "date": str(data_evento),
            "turno": turno,
            "qtd_pessoas": int(qtd_pessoas),
            "status": status,
            "sinal_pago": sinal_pago,
            "valor_locacao": float(valor_locacao),
            "valor_sinal": float(valor_sinal),
            "valor_caucao": float(valor_caucao),
            "taxa_extra": float(taxa_extra),
            "aluguel_som": float(aluguel_som),
            "qtd_chopp": int(qtd_chopp),
            "preco_litro_chopp": float(preco_litro_chopp),
            "estilo_chopp": estilo_chopp,
            "observacoes": observacoes,
        }
        reservas.append(nova_reserva)
        if salvar_no_github(reservas):
          st.success("Nova negociação/locação salva com sucesso na nuvem!")
          st.rerun()

elif menu == "📅 Painel / Calendário":
  # --- MONTAGEM DO CALENDÁRIO COM SUPORTE A MÚLTIPLOS EVENTOS POR DIA ---
  calendar_events = []
  for ev in eventos_filtrados:
    status_ev = ev.get("status", "Pendente")
    
    if status_ev == "Confirmado":
      icone_status = "✅ [Locado]"
      cor_fundo = "#28a745"  # Verde
    elif status_ev == "Cancelado":
      icone_status = "❌ [Cancelado]"
      cor_fundo = "#dc3545"  # Vermelho
    else:
      icone_status = "⏳ [Em Negociação]"
      cor_fundo = "#ffc107"  # Amarelo/Laranja

    sinal_txt = "Sinal OK" if ev.get("sinal_pago") else "Sinal Pendente"
    
    chopp_qtd = ev.get('qtd_chopp', 0)
    chopp_txt = f" | 🍺 {chopp_qtd}L {ev.get('estilo_chopp')}" if chopp_qtd > 0 else ""

    tipo_ev_str = f" ({ev.get('tipo_evento')})" if ev.get('tipo_evento') else ""
    data_exibicao_cal = formatar_data_br(ev.get("date"))
    titulo_cal = (
        f"[{data_exibicao_cal}] {icone_status} {ev.get('cliente')}{tipo_ev_str}"
        f" - {ev.get('turno')} | {ev.get('qtd_pessoas')} pes. ({sinal_txt}){chopp_txt}"
    )

    calendar_events.append({
        "title": titulo_cal,
        "start": ev.get("date"),
        "allDay": True,
        "backgroundColor": cor_fundo,
        "borderColor": cor_fundo,
    })

  calendar_options = {
      "headerToolbar": {
          "left": "prev,next",
          "center": "title",
          "right": "today",
      },
      "initialView": "dayGridMonth",
      "editable": False,
      "selectable": True,
      "locale": "pt-br",
  }

  st.subheader("📆 Calendário de Locações")
  calendar(events=calendar_events, options=calendar_options, key="calendar_salao")

  # --- GERENCIAMENTO OTIMIZADO E LIMPO ---
  st.divider()
  st.subheader("📋 Gerenciamento e Lista de Locações")

  if eventos_filtrados:
    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
      filtro_status_ger = st.selectbox(
          "Filtrar por Status nesta Lista",
          ["Todos", "Confirmado", "Pendente", "Cancelado"]
      )
    with col_f2:
      busca_cliente = st.text_input("🔍 Buscar por nome do cliente", "")

    lista_gerenciar = eventos_filtrados
    if filtro_status_ger != "Todos":
      lista_gerenciar = [e for e in lista_gerenciar if e.get("status") == filtro_status_ger]
    if busca_cliente.strip():
      lista_gerenciar = [e for e in lista_gerenciar if busca_cliente.lower() in e.get("cliente", "").lower()]

    eventos_ordenados = sorted(lista_gerenciar, key=lambda x: x["date"])

    if not eventos_ordenados:
      st.info("Nenhum evento encontrado com os filtros aplicados.")
    else:
      st.write(f"Mostrando **{len(eventos_ordenados)}** registro(s):")
      
      for ev in eventos_ordenados:
        ev_id = ev.get("id")
        status_ev = ev.get("status", "Pendente")
        emoji_status = "✅" if status_ev == "Confirmado" else ("❌" if status_ev == "Cancelado" else "⏳")
        data_br = formatar_data_br(ev.get('date'))
        sinal_txt = "✅ Sinal Pago" if ev.get("sinal_pago") else "⏳ Sinal Pendente"
        tipo_ev_lbl = f" ({ev.get('tipo_evento')})" if ev.get('tipo_evento') else ""

        with st.container(border=True):
          col_info, col_botoes = st.columns([3, 1])
          
          with col_info:
            st.markdown(f"**{emoji_status} {data_br} - {ev.get('cliente')}**{tipo_ev_lbl}")
            st.caption(f"Turno: **{ev.get('turno')}** | Pessoas: **{ev.get('qtd_pessoas')}** | Status: **{status_ev}** | {sinal_txt}")
            
            v_loc = ev.get("valor_locacao", 0.0)
            v_sin = ev.get("valor_sinal", 0.0)
            st.text(f"Locação: R$ {v_loc:,.2f} | Sinal (50%): R$ {v_sin:,.2f}")

          with col_botoes:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            btn_detalhes = st.button("👁️ Detalhes / Editar", key=f"btn_det_{ev_id}", use_container_width=True)
            btn_excluir = st.button("🗑️ Excluir", key=f"btn_exc_{ev_id}", use_container_width=True)

          if btn_excluir:
            reservas = [r for r in reservas if r.get("id") != ev_id]
            if salvar_no_github(reservas):
              st.success("Evento excluído com sucesso!")
              st.rerun()

          if btn_detalhes:
            st.session_state[f"modal_edit_{ev_id}"] = not st.session_state.get(f"modal_edit_{ev_id}", False)

          if st.session_state.get(f"modal_edit_{ev_id}", False):
            st.divider()
            st.markdown(f"### ✍️ Editando Locação: {ev.get('cliente')}")
            
            c_cli = st.text_input("Nome do Cliente", value=ev.get("cliente", ""), key=f"ec_{ev_id}")
            c_tel = st.text_input("Telefone / WhatsApp", value=ev.get("telefone", ""), key=f"et_{ev_id}")
            c_tipo = st.text_input("Tipo de Evento", value=ev.get("tipo_evento", ""), key=f"etip_{ev_id}")

            try:
              data_obj = datetime.strptime(ev.get("date", "2026-01-01"), "%Y-%m-%d").date()
            except:
              data_obj = datetime.now().date()
            c_data = st.date_input("Data da Locação", value=data_obj, key=f"edat_{ev_id}")

            turnos_lista = ["Manhã", "Tarde", "Noite", "Dia Inteiro"]
            idx_turno = turnos_lista.index(ev.get("turno")) if ev.get("turno") in turnos_lista else 0
            c_turno = st.selectbox("Turno", turnos_lista, index=idx_turno, key=f"etur_{ev_id}")

            c_pess = st.number_input("Headcount (Qtd de Pessoas)", min_value=1, value=int(ev.get("qtd_pessoas", 50)), step=1, key=f"epes_{ev_id}")

            status_lista = ["Confirmado", "Pendente", "Cancelado"]
            idx_status = status_lista.index(ev.get("status")) if ev.get("status") in status_lista else 0
            c_status = st.selectbox("Status da Locação", status_lista, index=idx_status, key=f"esta_{ev_id}")

            c_sinal = st.checkbox("50% de Sinal Pago?", value=bool(ev.get("sinal_pago", False)), key=f"esin_{ev_id}")

            c_vloc = st.number_input("Valor da Locação (R$)", min_value=0.0, value=float(ev.get("valor_locacao", 0.0)), step=50.0, format="%.2f", key=f"evloc_{ev_id}")
            c_vsin = st.number_input("Valor do Sinal - 50% (R$)", min_value=0.0, value=float(ev.get("valor_sinal", 0.0)), step=50.0, format="%.2f", key=f"evsin_{ev_id}")
            c_vcau = st.number_input("Valor da Caução (R$)", min_value=0.0, value=float(ev.get("valor_caucao", 0.0)), step=50.0, format="%.2f", key=f"evcau_{ev_id}")
            c_text = st.number_input("Taxa Extra (R$)", min_value=0.0, value=float(ev.get("taxa_extra", 0.0)), step=10.0, format="%.2f", key=f"evtex_{ev_id}")
            c_som = st.number_input("Aluguel de Som (R$)", min_value=0.0, value=float(ev.get("aluguel_som", 0.0)), step=50.0, format="%.2f", key=f"evsom_{ev_id}")

            c_chopp = st.number_input("Volume de Chopp (Litros)", min_value=0, value=int(ev.get("qtd_chopp", 0)), step=10, key=f"echo_{ev_id}")
            c_preco_chopp = st.number_input("Preço do Litro (R$)", min_value=0.0, value=float(ev.get("preco_litro_chopp", 0.0)), step=1.0, format="%.2f", key=f"eprecho_{ev_id}")

            idx_estilo = ESTILOS_CHOPP.index(ev.get("estilo_chopp")) if ev.get("estilo_chopp") in ESTILOS_CHOPP else 0
            c_estilo = st.selectbox("Estilo do Chopp", ESTILOS_CHOPP, index=idx_estilo, key=f"eest_{ev_id}")

            c_obs = st.text_area("Observações Gerais", value=ev.get("observacoes", ""), key=f"eobs_{ev_id}")

            if ev.get("telefone"):
              tel_limpo = ev.get("telefone").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
              st.markdown(f"[💬 Abrir WhatsApp do Cliente](https://wa.me/55{tel_limpo})")

            col_salvar, col_cancelar = st.columns(2)
            with col_salvar:
              if st.button("💾 Salvar Alterações", key=f"bsav_{ev_id}"):
                for item in reservas:
                  if item.get("id") == ev_id:
                    item["cliente"] = c_cli
                    item["telefone"] = c_tel
                    item["tipo_evento"] = c_tipo
                    item["date"] = str(c_data)
                    item["turno"] = c_turno
                    item["qtd_pessoas"] = int(c_pess)
                    item["status"] = c_status
                    item["sinal_pago"] = c_sinal
                    item["valor_locacao"] = float(c_vloc)
                    item["valor_sinal"] = float(c_vsin)
                    item["valor_caucao"] = float(c_vcau)
                    item["taxa_extra"] = float(c_text)
                    item["aluguel_som"] = float(c_som)
                    item["qtd_chopp"] = int(c_chopp)
                    item["preco_litro_chopp"] = float(c_preco_chopp)
                    item["estilo_chopp"] = c_estilo
                    item["observacoes"] = c_obs
                    break

                if salvar_no_github(reservas):
                  st.session_state[f"modal_edit_{ev_id}"] = False
                  st.success("Alterações salvas com sucesso!")
                  st.rerun()

            with col_cancelar:
              if st.button("❌ Fechar Edição", key=f"bcanc_{ev_id}"):
                st.session_state[f"modal_edit_{ev_id}"] = False
                st.rerun()
  else:
    st.info("Nenhum evento encontrado para este filtro.")
