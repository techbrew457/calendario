import base64
from datetime import datetime, time
import json
import os
import requests
import streamlit as st
from streamlit_calendar import calendar

# Configuração da página para ocupar a tela inteira (ótimo para celular)
st.set_page_config(
    page_title="Agenda - Salão de Festas", page_icon="📅", layout="wide"
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


# Carrega as reservas da nuvem
reservas, _ = carregar_reservas()

st.title("🎉 Gerenciamento de Locações - Salão de Festas")

# --- MENU LATERAL: CADASTRO E FILTROS ---
st.sidebar.header("⚙️ Opções & Cadastro")
menu = st.sidebar.radio(
    "Navegação", ["📅 Painel / Calendário", "➕ Nova Locação"]
)

# Filtros rápidos na barra lateral
st.sidebar.divider()
st.sidebar.subheader("🔍 Filtros")
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

# Filtragem de eventos
eventos_filtrados = reservas
if filtro_mes != "Todos":
  eventos_filtrados = [
      e for e in reservas if e.get("date", "").split("-")[1] == filtro_mes
  ]

if menu == "➕ Nova Locação":
  st.subheader("📝 Registrar Nova Locação")
  with st.form("form_cadastro", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
      cliente = st.text_input("Nome do Cliente")
      telefone = st.text_input("Telefone / WhatsApp (Ex: 42999999999)")
      tipo_evento = st.selectbox(
          "Tipo de Evento",
          ["Aniversário", "Casamento", "Confraternização", "Infantil", "Outros"],
      )
      data_evento = st.date_input("Data da Locação")
    with col2:
      turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite", "Dia Inteiro"])
      qtd_pessoas = st.number_input(
          "Headcount (Qtd de Pessoas)", min_value=1, value=50, step=1
      )
      status = st.selectbox(
          "Status da Locação", ["Confirmado", "Pendente", "Cancelado"]
      )
      sinal_pago = st.checkbox("50% de Sinal Pago?")

    st.divider()
    st.subheader("🍺 Opcionais & Observações")
    col3, col4 = st.columns(2)
    with col3:
      qtd_chopp = st.number_input(
          "Volume de Chopp (Litros)", min_value=0, value=0, step=10
      )
    with col4:
      estilo_chopp = st.selectbox(
          "Estilo do Chopp", ["Pilsen", "IPA", "Stout", "Weiss", "Nenhum"]
      )

    observacoes = st.text_area("Observações Gerais")

    submitted = st.form_submit_button("Salvar Locação no Sistema")
    if submitted:
      if not cliente.strip():
        st.warning("Por favor, preencha o nome do cliente.")
      else:
        novo_id = str(len(reservas) + 1)
        # Evitar ID duplicado se houver exclusões anteriores
        while any(r.get("id") == novo_id for r in reservas):
          novo_id = str(int(novo_id) + 1)

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
            "qtd_chopp": int(qtd_chopp),
            "estilo_chopp": estilo_chopp,
            "observacoes": observacoes,
        }
        reservas.append(nova_reserva)
        if salvar_no_github(reservas):
          st.success("Locação salva com sucesso na nuvem!")
          st.rerun()

elif menu == "📅 Painel / Calendário":
  # --- MONTAGEM DO CALENDAR COM ÍCONES DE STATUS ---
  calendar_events = []
  for ev in reservas:
    # Definindo cor ou ícone pelo status e sinal
    sinal_txt = "✅" if ev.get("sinal_pago") else "⏳"
    titulo_cal = (
        f"{sinal_txt} {ev.get('cliente')} ({ev.get('tipo_evento')})"
    )

    cor_fundo = "#28a745" if ev.get("status") == "Confirmado" else "#ffc107"
    if ev.get("status") == "Cancelado":
      cor_fundo = "#dc3545"

    calendar_events.append({
        "title": titulo_cal,
        "start": ev.get("date"),
        "allDay": True,
        "backgroundColor": cor_fundo,
        "borderColor": cor_fundo,
    })

  calendar_options = {
      "headerToolbar": {
          "left": "prev,next today",
          "center": "title",
          "right": "dayGridMonth,timeGridWeek",
      },
      "initialView": "dayGridMonth",
      "editable": False,
      "selectable": True,
      "locale": "pt-br",
  }

  st.subheader("📆 Calendário de Locações")
  calendar(
      events=calendar_events, options=calendar_options, key="calendar_salao"
  )

  # --- LISTA RÁPIDA E EDIÇÃO DE EVENTOS ABAIXO DO CALENDÁRIO ---
  st.divider()
  st.subheader("📋 Gerenciar Eventos & Detalhes")

  if eventos_filtrados:
    for ev in sorted(eventos_filtrados, key=lambda x: x["date"]):
      sinal_status = (
          "✅ Sinal Pago" if ev.get("sinal_pago") else "⏳ Sinal Pendente"
      )

      with st.expander(
          f"📌 {ev.get('date')} — {ev.get('cliente')} ({ev.get('tipo_evento')})"
      ):
        # Se o usuário clicou para editar este evento específico
        edit_key = f"edit_mode_{ev.get('id')}"
        if edit_key not in st.session_state:
          st.session_state[edit_key] = False

        if not st.session_state[edit_key]:
          # Modo de Visualização Normal
          st.write(f"**Tipo:** {ev.get('tipo_evento')}")
          st.write(
              f"**Status:** {ev.get('status')} | **Financeiro:**"
              f" {sinal_status}"
          )
          st.write(
              f"**Turno:** {ev.get('turno')} | **Headcount:**"
              f" {ev.get('qtd_pessoas')} pessoas"
          )
          if ev.get("telefone"):
            st.write(f"**Contato:** {ev.get('telefone')}")
            tel_limpo = (
                ev.get("telefone")
                .replace(" ", "")
                .replace("-", "")
                .replace("(", "")
                .replace(")", "")
            )
            st.markdown(
                f"[💬 Chamar no WhatsApp](https://wa.me/55{tel_limpo})"
            )
          if ev.get("qtd_chopp", 0) > 0:
            st.write(
                f"**Chopp:** {ev.get('qtd_chopp')}L ({ev.get('estilo_chopp')})"
            )
          if ev.get("observacoes"):
            st.write(f"**Obs:** {ev.get('observacoes')}")

          col_b1, col_b2 = st.columns(2)
          with col_b1:
            if st.button("✏️ Editar Dados", key=f"btn_edit_{ev.get('id')}"):
              st.session_state[edit_key] = True
              st.rerun()
          with col_b2:
            if st.button(
                "🗑️ Excluir Evento", key=f"btn_del_{ev.get('id')}"
            ):
              reservas = [r for r in reservas if r.get("id") != ev.get("id")]
              if salvar_no_github(reservas):
                st.success("Evento excluído com sucesso!")
                st.rerun()

        else:
          # Modo de Edição Completa
          st.markdown("### ✍️ Editando Locação")
          with st.form(key=f"form_edit_{ev.get('id')}"):
            c_cli = st.text_input(
                "Nome do Cliente", value=ev.get("cliente", "")
            )
            c_tel = st.text_input(
                "Telefone / WhatsApp", value=ev.get("telefone", "")
            )

            tipos_lista = [
                "Aniversário",
                "Casamento",
                "Confraternização",
                "Infantil",
                "Outros",
            ]
            idx_tipo = (
                tipos_lista.index(ev.get("tipo_evento"))
                if ev.get("tipo_evento") in tipos_lista
                else 0
            )
            c_tipo = st.selectbox(
                "Tipo de Evento", tipos_lista, index=idx_tipo
            )

            try:
              data_obj = datetime.strptime(
                  ev.get("date", "2026-01-01"), "%Y-%m-%d"
              ).date()
            except:
              data_obj = datetime.now().date()
            c_data = st.date_input("Data da Locação", value=data_obj)

            turnos_lista = ["Manhã", "Tarde", "Noite", "Dia Inteiro"]
            idx_turno = (
                turnos_lista.index(ev.get("turno"))
                if ev.get("turno") in turnos_lista
                else 0
            )
            c_turno = st.selectbox("Turno", turnos_lista, index=idx_turno)

            c_pess = st.number_input(
                "Headcount (Qtd de Pessoas)",
                min_value=1,
                value=int(ev.get("qtd_pessoas", 50)),
                step=1,
            )

            status_lista = ["Confirmado", "Pendente", "Cancelado"]
            idx_status = (
                status_lista.index(ev.get("status"))
                if ev.get("status") in status_lista
                else 0
            )
            c_status = st.selectbox(
                "Status da Locação", status_lista, index=idx_status
            )

            c_sinal = st.checkbox(
                "50% de Sinal Pago?", value=bool(ev.get("sinal_pago", False))
            )

            c_chopp = st.number_input(
                "Volume de Chopp (Litros)",
                min_value=0,
                value=int(ev.get("qtd_chopp", 0)),
                step=10,
            )

            estilos_lista = ["Pilsen", "IPA", "Stout", "Weiss", "Nenhum"]
            idx_estilo = (
                estilos_lista.index(ev.get("estilo_chopp"))
                if ev.get("estilo_chopp") in estilos_lista
                else 0
            )
            c_estilo = st.selectbox(
                "Estilo do Chopp", estilos_lista, index=idx_estilo
            )

            c_obs = st.text_area(
                "Observações Gerais", value=ev.get("observacoes", "")
            )

            col_salvar, col_cancelar = st.columns(2)
            with col_salvar:
              salvar_edicao = st.form_submit_button("💾 Salvar Alterações")
            with col_cancelar:
              cancelar_edicao = st.form_submit_button("❌ Cancelar")

            if salvar_edicao:
              # Atualiza os dados na lista
              for item in reservas:
                if item.get("id") == ev.get("id"):
                  item["cliente"] = c_cli
                  item["telefone"] = c_tel
                  item["tipo_evento"] = c_tipo
                  item["date"] = str(c_data)
                  item["turno"] = c_turno
                  item["qtd_pessoas"] = int(c_pess)
                  item["status"] = c_status
                  item["sinal_pago"] = c_sinal
                  item["qtd_chopp"] = int(c_chopp)
                  item["estilo_chopp"] = c_estilo
                  item["observacoes"] = c_obs
                  break

              if salvar_no_github(reservas):
                st.session_state[edit_key] = False
                st.success("Alterações salvas com sucesso!")
                st.rerun()

            if cancelar_edicao:
              st.session_state[edit_key] = False
              st.rerun()
  else:
    st.info("Nenhum evento encontrado para este filtro.")
