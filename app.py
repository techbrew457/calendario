import json
import os
import streamlit as st
from streamlit_calendar import calendar

# Configuração da página para ocupar a tela inteira (ótimo para celular)
st.set_page_config(
    page_title="Agenda - Salão de Festas", page_icon="📅", layout="wide"
)

# Arquivo JSON para salvar as reservas permanentemente na nuvem
ARQUIVO_DADOS = "reservas.json"


def carregar_reservas():
  if os.path.exists(ARQUIVO_DADOS):
    with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
      return json.load(f)
  return []


def salvar_reservas(reservas):
  with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
    json.dump(reservas, f, ensure_ascii=False, indent=4)


# Carrega as reservas salvas
eventos = carregar_reservas()

st.title("🎉 Agenda de Locação - Salão de Festas")
st.markdown("Consulte os dias ocupados ou faça o login para gerenciar.")

# --- BARRA LATERAL: CONTROLE DE ACESSO (LOGIN) ---
st.sidebar.header("Painel de Controle")
senha_digitada = st.sidebar.text_input("Senha de Administrador", type="password")

# Defina sua senha de acesso aqui (mude para a que preferir)
SENHA_MESTRA = "admin123"
autorizado = senha_digitada == SENHA_MESTRA

if autorizado:
  st.sidebar.success("Modo Edição Ativado ✅")
else:
  st.sidebar.info("Modo Apenas Visualização 👁️ (Digite a senha para editar)")

# --- ÁREA DE EDIÇÃO (APENAS PARA QUEM TEM A SENHA) ---
if autorizado:
  st.subheader("➕ Adicionar Nova Locação")
  with st.form("form_reserva", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
      nome_cliente = st.text_input("Nome do Cliente / Evento")
      data_evento = st.date_input("Data da Festa")
    with col2:
      horario = st.text_input(
          "Horário (Ex: 14:00 às 22:00)", value="Das 08h às 22h"
      )
      observacoes = st.text_input("Detalhes (Opcional)", value="Pago / Confirmado")

    botao_salvar = st.form_submit_button("Salvar Locação")

    if botao_salvar:
      if nome_cliente:
        # Formato exigido pelo calendário
        novo_evento = {
            "title": f"🔒 {nome_cliente} ({horario})",
            "date": str(data_evento),
            "backgroundColor": "#FF4B4B",
            "borderColor": "#FF4B4B",
            "textColor": "#ffffff",
        }
        eventos.append(novo_evento)
        salvar_reservas(eventos)
        st.success(f"Reserva para {nome_cliente} adicionada com sucesso!")
        st.rerun()
      else:
        st.error("Por favor, preencha o nome do cliente.")

  # Opção para excluir evento
  if eventos:
    st.subheader("🗑️ Remover Locação")
    titulos_eventos = [e["title"] for e in eventos]
    evento_para_remover = st.selectbox(
        "Selecione o evento para cancelar", titulos_eventos
    )
    if st.button("Excluir Evento Selecionado"):
      eventos = [e for e in eventos if e["title"] != evento_para_remover]
      salvar_reservas(eventos)
      st.warning("Evento removido com sucesso!")
      st.rerun()

st.divider()

# --- EXIBIÇÃO DO CALENDARIZADOR (VISÍVEL PARA TODOS) ---
st.subheader("📅 Calendário de Reservas")

# Configurações de visualização do calendário (estilo Google Agenda)
calendar_options = {
    "editable": False,
    "selectable": True,
    "initialView": "dayGridMonth",  # Visão de mês por padrão (ótimo para celular)
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek",
    },
    "locale": "pt-br",
}

# Renderiza o componente de calendário na tela
calendar(events=eventos, options=calendar_options, key="calendario_salao")