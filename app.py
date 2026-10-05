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
      "Erro: As credenciais do GitHub (GITHUB_TOKEN e GITHUB_REPO) não foram"
      " encontradas nos Secrets do Streamlit."
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
  conteudo_base64 = base64.b64encode(novo_conteudo.encode("utf-8")).decode(
      "utf-8"
  )

  dados = {
      "message": "Atualização de reservas via app do salão",
      "content": conteudo_base64,
  }
  if sha:
    dados["sha"] = sha

  response = requests.put(url, headers=HEADERS, json=dados)
  if response.status_code not in [200, 201]:
    st.error(
        f"Erro ao salvar no GitHub ({response.status_code}):"
        f" {response.json().get('message', 'Erro desconhecido')}"
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
  
  menu = st.radio(
      "Navegação", ["📅 Painel / Calendário", "➕ Nova Locação"]
  )

  st.divider()
  st.subheader("🔍 Filtros")
  filtro_mes = st.sidebar.selectbox(
      "Filtrar por Mês (Opcional)",
      [
          "Todos",
          "01",
          "02",
          "03",
          "04",
          "05",
          "06",
          "07",
          "08",
          "09",
          "10",
          "11",
          "12",
      ],
  )

st.title("🍻 Reservas Espaço - Koch Cervejaria")

# Lista oficial de estilos de chopp da cervejaria
ESTILOS_CHOPP = [
    "Bohemian Pilsener",
    "Premium Golden",
    "APA",
    "Vinho",
    "Red Ale",
    "Nenhum",
]

# Filtragem de eventos
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
      tipo_evento = st.selectbox(
          "Tipo de Evento",
          ["Aniversário", "Casamento", "Confraternização", "Infantil", "Outros"],
      )
      data_evento =
