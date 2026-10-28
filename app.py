import base64
from datetime import datetime
import io
import json
import os
from docx import Document
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
            dados = json.loads(conteudo_bytes.decode("utf-8"))
            for idx, item in enumerate(dados):
                if not item.get("id"):
                    item["id"] = f"res-{idx}-{str(item.get('cliente','sem')).replace(' ','')}"
            return dados, dados_resp["sha"]
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


def gerar_documento_word(ev, data_formatada, barris, texto_opcionais_contrato, texto_barris_contrato):
    caminho_modelo = "modelo_contrato.docx"
    if not os.path.exists(caminho_modelo):
        return None

    doc = Document(caminho_modelo)

    # Cálculo dos totais para o contrato
    v_loc = float(ev.get('valor_locacao', 0) or 0)
    v_som = float(ev.get('valor_som', 0) or 0) if ev.get('som_sn') == 'Sim' else 0
    v_ret = float(ev.get('valor_retroprojetor', 0) or 0) if ev.get('retro_sn') == 'Sim' else 0
    v_taxa = float(ev.get('valor_taxa_adicional', 0) or 0)
    v_ref = float(ev.get('refri_val', 0) or 0) if ev.get('refri_sn') == 'Sim' else 0
    v_ag = float(ev.get('aguag_val', 0) or 0) if ev.get('aguag_sn') == 'Sim' else 0
    v_as = float(ev.get('aguas_val', 0) or 0) if ev.get('aguas_sn') == 'Sim' else 0
    v_suc = float(ev.get('suco_val', 0) or 0) if ev.get('suco_sn') == 'Sim' else 0
    v_imp = float(ev.get('imp_val', 0) or 0) if ev.get('imp_sn') == 'Sim' else 0
    v_chopp = sum(float(b.get('valor_total', 0) or 0) for b in barris)
    
    total_geral = v_loc + v_som + v_ret + v_taxa + v_ref + v_ag + v_as + v_suc + v_imp + v_chopp
    v_sinal = float(ev.get('valor_sinal', 0) or 0)
    restante_pagar = total_geral - v_sinal

    contexto = {
        "{{cliente}}": str(ev.get("cliente", "")),
        "{{documento}}": str(ev.get("documento", "Não informado")),
        "{{telefone}}": str(ev.get("telefone", "")),
        "{{data}}": str(data_formatada),
        "{{turno}}": str(ev.get("turno", "")),
        "{{qtd_pessoas}}": str(ev.get("qtd_pessoas", 0)),
        "{{tipo_evento}}": str(ev.get("tipo_evento", "Festividade")),
        "{{valor_locacao}}": f"R$ {v_loc:,.2f}",
        "{{valor_sinal}}": f"R$ {v_sinal:,.2f}",
        "{{status_sinal}}": "Pago" if (v_sinal > 0 or ev.get("sinal_pago")) else "Pendente",
        "{{valor_caucao}}": f"R$ {float(ev.get('valor_caucao', 0) or 0):,.2f}",
        "{{valor_total}}": f"R$ {total_geral:,.2f}",
        "{{restante_pagar}}": f"R$ {restante_pagar:,.2f}",
        "{{opcionais}}": texto_opcionais_contrato,
        "{{chopps}}": texto_barris_contrato,
        "{{observacoes}}": str(ev.get("observacoes", "Nenhuma observação específica registrada."))
    }

    for p in doc.paragraphs:
        for chave, valor in contexto.items():
            if chave in p.text:
                for run in p.runs:
                    if chave in run.text:
                        run.text = run.text.replace(chave, valor)
                if chave in p.text:
                    p.text = p.text.replace(chave, valor)

    for tabela in doc.tables:
        for linha in tabela.rows:
            for celula in linha.cells:
                for chave, valor in contexto.items():
                    if chave in celula.text:
                        celula.text = celula.text.replace(chave, valor)

    arquivo_io = io.BytesIO()
    doc.save(arquivo_io)
    arquivo_io.seek(0)
    return arquivo_io


# Carregar dados em memória
reservas, _ = carregar_dados_nuvem()

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
    eventos_filtrados = [e for e in eventos_filtrados if str(e.get("date", "")).split("-")[1] == filtro_mes]


# ==========================================
# 1. DASHBOARD & MÉTRICAS FINANCEIRAS
# ==========================================
if menu == "📊 Dashboard & Métricas":
    st.title("📊 Painel de Controle Consolidado")
    st.markdown("Visão executiva em tempo real do faturamento e ocupação.")

    total_locacoes = len(eventos_filtrados)
    confirmados = sum(1 for e in eventos_filtrados if e.get("status") == "Confirmado")
    pendentes = sum(1 for e in eventos_filtrados if e.get("status") == "Pendente")
    
    faturamento_projetado = sum(float(e.get("valor_locacao", 0) or 0) for e in eventos_filtrados if e.get("status"] != "Cancelado")
    
    sinais_recebidos = sum(
        float(e.get("valor_sinal", 0) or 0) 
        for e in eventos_filtrados 
        if e.get("status") != "Cancelado" and (float(e.get("valor_sinal", 0) or 0) > 0 or e.get("sinal_pago"))
    )
    
    total_chopp_litros = 0
    for e in eventos_filtrados:
        if e.get("status") != "Cancelado":
            barris = e.get("barris", [])
            for b in barris:
                total_chopp_litros += int(b.get("litros", 0) or 0)

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
                "Locação (R$)": f"R$ {float(e.get('valor_locacao', 0) or 0):,.2f}"
            } for e in sorted(eventos_filtrados, key=lambda x: str(x.get("date", "")))],
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

        sinal_txt = "Sinal OK" if (float(ev.get("valor_sinal", 0) or 0) > 0 or ev.get("sinal_pago")) else "Sinal Pendente"
        
        barris = ev.get("barris", [])
        total_litros_ev = sum(int(b.get("litros", 0) or 0) for b in barris)
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
    st.markdown("Preencha os dados, opcionais, bebidas, itens extras e valores.")

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
                ano_ev = st.selectbox("Ano", [2025, 2026, 2027, 2028], index=1, key="d_ano")

            turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite", "Dia Inteiro"])
            qtd_pessoas = st.number_input("Qtdade de Pessoas", min_value=1, value=50, step=1)

        st.divider()
        st.subheader("🔊 Opcionais e Serviços Adicionais")
        
        col_op1, col_op2 = st.columns(2)
        with col_op1:
            som_sn = st.selectbox("Caixa de Som?", ["Não", "Sim"], index=0, key="som_sn")
            valor_som = st.number_input("Valor Caixa de Som (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="v_som")
            cuidador_sn = st.selectbox("Monitor / Cuidador?", ["Não", "Sim"], index=0, key="cuid_sn")
        with col_op2:
            retro_sn = st.selectbox("Retroprojetor?", ["Não", "Sim"], index=0, key="retro_sn")
            valor_retroprojetor = st.number_input("Valor Retroprojetor (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="v_retro")
            valor_taxa_adicional = st.number_input("Taxa Adicional / Extra (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="v_taxa_ad")

        st.divider()
        st.subheader("🥤 Bebidas Consignadas e Água / Suco")

        col_beb1, col_beb2 = st.columns(2)
        with col_beb1:
            st.markdown("##### 🥤 Refrigerantes em Consignação")
            refri_sn = st.selectbox("Incluir Refrigerantes?", ["Não", "Sim"], index=0, key="refri_sn")
            refri_marca = st.text_input("Marca dos Refrigerantes", key="refri_marca")
            refri_val = st.number_input("Valor / Acordo Refri (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="refri_val")

            st.markdown("##### 💧 Água com Gás - Barril")
            aguag_sn = st.selectbox("Incluir Água com Gás (Barril)?", ["Não", "Sim"], index=0, key="aguag_sn")
            aguag_marca = st.text_input("Marca Água com Gás", key="aguag_marca")
            aguag_val = st.number_input("Valor Água com Gás (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="aguag_val")

        with col_beb2:
            st.markdown("##### 🚰 Água Sem Gás - Garrafa")
            aguas_sn = st.selectbox("Incluir Água Sem Gás (Garrafa)?", ["Não", "Sim"], index=0, key="aguas_sn")
            aguas_marca = st.text_input("Marca Água Sem Gás", key="aguas_marca")
            aguas_val = st.number_input("Valor Água Sem Gás (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="aguas_val")

            st.markdown("##### 🧃 Suco Lata")
            suco_sn = st.selectbox("Incluir Suco Lata?", ["Não", "Sim"], index=0, key="suco_sn")
            suco_marca = st.text_input("Marca Suco Lata", key="suco_marca")
            suco_val = st.number_input("Valor Suco Lata (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="suco_val")

        st.divider()
        st.subheader("🛠️ Item Improvisado / Extra")
        col_imp1, col_imp2, col_imp3, col_imp4 = st.columns(4)
        with col_imp1:
            imp_desc = st.text_input("Descrição do Item", key="imp_desc")
        with col_imp2:
            imp_sn = st.selectbox("Incluir Item?", ["Não", "Sim"], index=0, key="imp_sn")
        with col_imp3:
            imp_marca = st.text_input("Marca / Modelo", key="imp_marca")
        with col_imp4:
            imp_val = st.number_input("Valor Item (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="imp_val")

        st.divider()
        st.subheader("🍺 Gestão de Múltiplos Barris de Chopp Koch (Opções: 30L ou 50L)")
        
        opt_litros_cad = [0, 50, 30]

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.markdown("##### 🛢️ Barril 1")
            estilo_1 = st.selectbox("Estilo 1", ["Nenhum"] + ESTILOS_CHOPP, key="e1")
            litros_1 = st.selectbox("Tamanho 1 (Litros)", opt_litros_cad, index=1, key="t1")
            valor_b1 = st.number_input("Valor do Barril 1 (R$)", min_value=0.0, value=300.0, step=10.0, format="%.2f", key="vb1")

            st.markdown("##### 🛢️ Barril 3")
            estilo_3 = st.selectbox("Estilo 3", ["Nenhum"] + ESTILOS_CHOPP, key="e3")
            litros_3 = st.selectbox("Tamanho 3 (Litros)", opt_litros_cad, index=0, key="t3")
            valor_b3 = st.number_input("Valor do Barril 3 (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="vb3")

        with col_b2:
            st.markdown("##### 🛢️ Barril 2")
            estilo_2 = st.selectbox("Estilo 2", ["Nenhum"] + ESTILOS_CHOPP, key="e2")
            litros_2 = st.selectbox("Tamanho 2 (Litros)", opt_litros_cad, index=0, key="t2")
            valor_b2 = st.number_input("Valor do Barril 2 (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="vb2")

            st.markdown("##### 🛢️ Barril 4")
            estilo_4 = st.selectbox("Estilo 4", ["Nenhum"] + ESTILOS_CHOPP, key="e4")
            litros_4 = st.selectbox("Tamanho 4 (Litros)", opt_litros_cad, index=0, key="t4")
            valor_b4 = st.number_input("Valor do Barril 4 (R$)", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="vb4")

        st.markdown("---")
        st.subheader("🔄 Chopp Consignado (Extra deixado em consignação)")
        col_con1, col_con2, col_con3 = st.columns(3)
        with col_con1:
            chopp_cons_sn = st.selectbox("Deixou Barril Consignado?", ["Não", "Sim"], index=0, key="c_cons_sn")
        with col_con2:
            chopp_cons_estilo = st.selectbox("Estilo Consignado", ["Nenhum"] + ESTILOS_CHOPP, key="c_cons_est")
        with col_con3:
            chopp_cons_litros = st.selectbox("Volume Consignado", [0, 30, 50], key="c_cons_lit")

        st.divider()
        st.subheader("💰 Comercial e Valores do Salão")
        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            valor_locacao = st.number_input("Valor da Locação (R$)", min_value=0.0, value=1000.0, step=50.0, format="%.2f")
        with col_v2:
            valor_sinal = st.number_input("Valor do Sinal / Pago (R$)", min_value=0.0, value=500.0, step=50.0, format="%.2f")
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
                    data_formatada_str = f"{ano_ev}-{int(mes_ev):02d}-{int(dia_ev):02d}"
                    datetime.strptime(data_formatada_str, "%Y-%m-%d")
                except ValueError:
                    st.error("⚠️ Data inválida. Verifique o dia e o mês selecionados.")
                    st.stop()

                lista_barris = []
                for est, lit, val in [
                    (estilo_1, litros_1, valor_b1),
                    (estilo_2, litros_2, valor_b2),
                    (estilo_3, litros_3, valor_b3),
                    (estilo_4, litros_4, valor_b4),
                ]:
                    if est != "Nenhum" and lit > 0:
                        lista_barris.append({"estilo": est, "litros": int(lit), "valor_total": float(val)})

                novo_id = str(int(datetime.now().timestamp()))
                nova_reserva = {
                    "id": novo_id,
                    "cliente": cliente,
                    "telefone": telefone,
                    "documento": documento,
                    "tipo_evento": tipo_evento,
                    "date": data_formatada_str,
                    "turno": turno,
                    "qtd_pessoas": int(qtd_pessoas),
                    "status": status,
                    "sinal_pago": sinal_pago,
                    "valor_locacao": float(valor_locacao),
                    "valor_sinal": float(valor_sinal),
                    "valor_caucao": float(valor_caucao),
                    "som_sn": som_sn,
                    "valor_som": float(valor_som),
                    "retro_sn": retro_sn,
                    "valor_retroprojetor": float(valor_retroprojetor),
                    "cuidador_sn": cuidador_sn,
                    "valor_taxa_adicional": float(valor_taxa_adicional),
                    "refri_sn": refri_sn, "refri_marca": refri_marca, "refri_val": float(refri_val),
                    "aguag_sn": aguag_sn, "aguag_marca": aguag_marca, "aguag_val": float(aguag_val),
                    "aguas_sn": aguas_sn, "aguas_marca": aguas_marca, "aguas_val": float(aguas_val),
                    "suco_sn": suco_sn, "suco_marca": suco_marca, "suco_val": float(suco_val),
                    "imp_desc": imp_desc, "imp_sn": imp_sn, "imp_marca": imp_marca, "imp_val": float(imp_val),
                    "barris": lista_barris,
                    "chopp_cons_sn": chopp_cons_sn,
                    "chopp_cons_estilo": chopp_cons_estilo,
                    "chopp_cons_litros": int(chopp_cons_litros),
                    "observacoes": observacoes,
                }
                reservas.append(nova_reserva)
                if salvar_dados_nuvem(reservas):
                    st.success("🎉 Locação registrada e salva com sucesso!")
                    st.rerun()


# ==========================================
# 4. LISTA & GESTÃO
# ==========================================
elif menu == "📋 Lista & Gestão":
    st.title("📋 Gerenciamento de Locações")
    st.markdown("Consulte, edite status, abra o WhatsApp direto ou gere o contrato em Word.")

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

        for ev in sorted(lista_exibicao, key=lambda x: str(x.get("date", ""))):
            ev_id = ev.get("id")
            st_ev = ev.get("status", "Pendente")
            emoji = "✅" if st_ev == "Confirmado" else ("❌" if st_ev == "Cancelado" else "⏳")
            data_formatada = formatar_data_br(ev.get("date"))

            with st.container(border=True):
                col_i1, col_i2 = st.columns([3, 1])
                with col_i1:
                    st.markdown(f"**{emoji} Data: {data_formatada} - {ev.get('cliente')}**")
                    st.caption(f"Turno: **{ev.get('turno')}** | Evento: {ev.get('tipo_evento', 'Festividade')} | Qtdade de Pessoas: {ev.get('qtd_pessoas', 0)} | Status: **{st_ev}**")
                    
                    tel = ev.get("telefone", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                    if tel:
                        st.markdown(f"[💬 Abrir Conversa no WhatsApp](https://wa.me/55{tel})")
                    
                    # Cálculos financeiros detalhados por evento
                    v_loc = float(ev.get("valor_locacao", 0) or 0)
                    v_som = float(ev.get("valor_som", 0) or 0) if ev.get("som_sn") == "Sim" else 0
                    v_ret = float(ev.get("valor_retroprojetor", 0) or 0) if ev.get("retro_sn") == "Sim" else 0
                    v_taxa = float(ev.get("valor_taxa_adicional", 0) or 0)
                    v_ref = float(ev.get("refri_val", 0) or 0) if ev.get("refri_sn") == "Sim" else 0
                    v_ag = float(ev.get("aguag_val", 0) or 0) if ev.get("aguag_sn") == "Sim" else 0
                    v_as = float(ev.get("aguas_val", 0) or 0) if ev.get("aguas_sn") == "Sim" else 0
                    v_suc = float(ev.get("suco_val", 0) or 0) if ev.get("suco_sn") == "Sim" else 0
                    v_imp = float(ev.get("imp_val", 0) or 0) if ev.get("imp_sn") == "Sim" else 0
                    
                    barris = ev.get("barris", [])
                    v_chopp_total = sum(float(b.get("valor_total", 0) or 0) for b in barris)
                    
                    total_venda = v_loc + v_som + v_ret + v_taxa + v_ref + v_ag + v_as + v_suc + v_imp + v_chopp_total
                    v_sinal_cadastrado = float(ev.get("valor_sinal", 0) or 0)
                    restante_a_pagar = total_venda - v_sinal_cadastrado
                    
                    desc_barris = ", ".join([f"{b['litros']}L {b['estilo']} (R$ {float(b.get('valor_total', 0) or 0):,.2f})" for b in barris]) if barris else "Nenhum chopp"

                    st.markdown(f"💰 **Total da Venda:** R$ {total_venda:,.2f} | 💵 **Já Pago (Sinal):** R$ {v_sinal_cadastrado:,.2f} | 🔴 **Falta Pagar:** **R$ {restante_a_pagar:,.2f}**")
                    st.text(f"Locação: R$ {v_loc:,.2f} | Som: R$ {v_som:,.2f} | Chopp: R$ {v_chopp_total:,.2f}")
                    st.text(f"Barris: {desc_barris}")
                    if ev.get('chopp_cons_sn') == "Sim":
                        st.text(f"🔄 Chopp Consignado: {ev.get('chopp_cons_litros')}L de {ev.get('chopp_cons_estilo')}")

                with col_i2:
                    btn_edit = st.button("✏️ Editar", key=f"ed_{ev_id}", use_container_width=True)
                    btn_contrato = st.button("📄 Contrato", key=f"ct_{ev_id}", use_container_width=True)
                    btn_del = st.button("🗑️ Excluir", key=f"dl_{ev_id}", use_container_width=True)

                if btn_del:
                    reservas = [r for r in reservas if r.get("id") != ev_id]
                    if salvar_dados_nuvem(reservas):
                        st.success("Reserva excluída com sucesso!")
                        st.rerun()

                if btn_contrato:
                    st.divider()
                    st.markdown("### 📄 Geração de Contrato em Word (.docx)")
                    
                    texto_barris_contrato = "\n".join([f"- {b['litros']} litros de Chopp estilo {b['estilo']} - R$ {float(b.get('valor_total', 0) or 0):,.2f}" for b in barris]) if barris else "Nenhum opcional de chopp."
                    if ev.get('chopp_cons_sn') == "Sim":
                        texto_barris_contrato += f"\n- Consignado Extra: {ev.get('chopp_cons_litros')}L de {ev.get('chopp_cons_estilo')} (Cobrado apenas se consumido)"
                    
                    texto_op_parts = []
                    if ev.get("som_sn") == "Sim":
                        texto_op_parts.append(f"- Caixa de Som: R$ {float(ev.get('valor_som', 0) or 0):,.2f}")
                    if ev.get("retro_sn") == "Sim":
                        texto_op_parts.append(f"- Retroprojetor: R$ {float(ev.get('valor_retroprojetor', 0) or 0):,.2f}")
                    if ev.get("cuidador_sn") == "Sim":
                        texto_op_parts.append("- Monitor / Cuidador: Incluso")
                    if float(ev.get("valor_taxa_adicional", 0) or 0) > 0:
                        texto_op_parts.append(f"- Taxa Adicional: R$ {float(ev.get('valor_taxa_adicional', 0) or 0):,.2f}")
                    if ev.get("refri_sn") == "Sim":
                        texto_op_parts.append(f"- Refrigerantes em Consignação (Marca: {ev.get('refri_marca','-')}): R$ {float(ev.get('refri_val',0) or 0):,.2f}")
                    if ev.get("aguag_sn") == "Sim":
                        texto_op_parts.append(f"- Água com Gás Barril (Marca: {ev.get('aguag_marca','-')}): R$ {float(ev.get('aguag_val',0) or 0):,.2f}")
                    if ev.get("aguas_sn") == "Sim":
                        texto_op_parts.append(f"- Água Sem Gás Garrafa (Marca: {ev.get('aguas_marca','-')}): R$ {float(ev.get('aguas_val',0) or 0):,.2f}")
                    if ev.get("suco_sn") == "Sim":
                        texto_op_parts.append(f"- Suco Lata (Marca: {ev.get('suco_marca','-')}): R$ {float(ev.get('suco_val',0) or 0):,.2f}")
                    if ev.get("imp_sn") == "Sim" and ev.get("imp_desc"):
                        texto_op_parts.append(f"- Item Extra ({ev.get('imp_desc')} - Marca: {ev.get('imp_marca','-')}): R$ {float(ev.get('imp_val',0) or 0):,.2f}")

                    texto_opcionais_contrato = "\n".join(texto_op_parts) if texto_op_parts else "Nenhum opcional contratado."

                    arquivo_docx = gerar_documento_word(ev, data_formatada, barris, texto_opcionais_contrato, texto_barris_contrato)
                    
                    if arquivo_docx:
                        nome_arquivo_download = f"Contrato_{str(ev.get('cliente','')).replace(' ', '_')}.docx"
                        st.download_button(
                            label="📥 Baixar Contrato em Word Preenchido",
                            data=arquivo_docx,
                            file_name=nome_arquivo_download,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_docx_{ev_id}"
                        )
                    else:
                        st.warning("⚠️ O arquivo `modelo_contrato.docx` não foi encontrado no GitHub. Certifique-se de enviá-lo para a raiz do repositório.")

                if btn_edit:
                    st.session_state[f"edit_mode_{ev_id}"] = not st.session_state.get(f"edit_mode_{ev_id}", False)

                if st.session_state.get(f"edit_mode_{ev_id}", False):
                    st.divider()
                    st.markdown(f"**Editando Completo: {ev.get('cliente')}**")
                    
                    with st.form(f"form_edit_{ev_id}"):
                        e_cli = st.text_input("Cliente", value=ev.get("cliente", ""), key=f"c_{ev_id}")
                        e_tel = st.text_input("WhatsApp", value=ev.get("telefone", ""), key=f"t_{ev_id}")
                        e_doc = st.text_input("CPF ou CNPJ", value=ev.get("documento", ""), key=f"doc_{ev_id}")
                        e_tipo_evento = st.text_input("Tipo de Evento", value=ev.get("tipo_evento", ""), key=f"te_{ev_id}")
                        
                        turnos_opcoes = ["Manhã", "Tarde", "Noite", "Dia Inteiro"]
                        turno_atual = ev.get("turno", "Noite")
                        idx_turno = turnos_opcoes.index(turno_atual) if turno_atual in turnos_opcoes else 0
                        e_turno = st.selectbox("Turno", turnos_opcoes, index=idx_turno, key=f"tur_{ev_id}")

                        e_qtd_pes = st.number_input("Qtdade de Pessoas", min_value=1, value=int(ev.get("qtd_pessoas", 50) or 50), step=1, key=f"qp_{ev_id}")
                        
                        try:
                            partes_dt = str(ev.get("date", "2026-01-01")).split("-")
                            ano_atu, mes_atu, dia_atu = int(partes_dt[0]), int(partes_dt[1]), int(partes_dt[2])
                        except Exception:
                            ano_atu, mes_atu, dia_atu = 2026, 1, 1

                        anos_disponiveis_edicao = [2025, 2026, 2027, 2028]
                        idx_ano_safe = anos_disponiveis_edicao.index(ano_atu) if ano_atu in anos_disponiveis_edicao else 1

                        st.markdown("**Editar Data (DD/MM/AAAA)**")
                        c_ed1, c_ed2, c_ed3 = st.columns(3)
                        with c_ed1:
                            e_dia = st.selectbox("Dia", list(range(1, 32)), index=max(0, dia_atu - 1), key=f"ed_dia_{ev_id}")
                        with c_ed2:
                            e_mes = st.selectbox("Mês", list(range(1, 13)), index=max(0, mes_atu - 1), format_func=lambda x: f"{x:02d}", key=f"ed_mes_{ev_id}")
                        with c_ed3:
                            e_ano = st.selectbox("Ano", anos_disponiveis_edicao, index=idx_ano_safe, key=f"ed_ano_{ev_id}")

                        status_lista = ["Pendente", "Confirmado", "Cancelado"]
                        idx_status = status_lista.index(ev.get("status", "Pendente")) if ev.get("status") in status_lista else 0
                        e_stat = st.selectbox("Status", status_lista, index=idx_status, key=f"s_{ev_id}")
                        
                        col_ev1, col_ev2, col_ev3 = st.columns(3)
                        with col_ev1:
                            e_vloc = st.number_input("Valor Locação (R$)", value=float(ev.get("valor_locacao", 0) or 0), step=50.0, key=f"vl_{ev_id}")
                        with col_ev2:
                            e_vsinal = st.number_input("Valor do Sinal / Pago (R$)", value=float(ev.get("valor_sinal", 0) or 0), step=50.0, key=f"vs_{ev_id}")
                        with col_ev3:
                            e_vcaucao = st.number_input("Valor Caução (R$)", value=float(ev.get("valor_caucao", 0) or 0), step=50.0, key=f"vc_{ev_id}")

                        st.markdown("---")
                        st.subheader("🔊 Opcionais")
                        c_op_e1, c_op_e2 = st.columns(2)
                        with c_op_e1:
                            idx_som = 0 if ev.get("som_sn") == "Sim" else 1
                            e_som_sn = st.selectbox("Caixa de Som?", ["Não", "Sim"], index=idx_som, key=f"e_som_sn_{ev_id}")
                            e_vsom = st.number_input("Valor Som", value=float(ev.get("valor_som", 0) or 0), step=10.0, key=f"e_vsom_{ev_id}")
                            idx_cuid = 0 if ev.get("cuidador_sn") == "Sim" else 1
                            e_cuid_sn = st.selectbox("Monitor / Cuidador?", ["Não", "Sim"], index=idx_cuid, key=f"e_cuid_sn_{ev_id}")
                        with c_op_e2:
                            idx_retro = 0 if ev.get("retro_sn") == "Sim" else 1
                            e_retro_sn = st.selectbox("Retroprojetor?", ["Não", "Sim"], index=idx_retro, key=f"e_retro_sn_{ev_id}")
                            e_vretro = st.number_input("Valor Retroprojetor", value=float(ev.get("valor_retroprojetor", 0) or 0), step=10.0, key=f"e_vretro_{ev_id}")
                            e_vtaxa_adicional = st.number_input("Taxa Adicional", value=float(ev.get("valor_taxa_adicional", 0) or 0), step=10.0, key=f"e_vtaxa_{ev_id}")

                        st.markdown("---")
                        st.subheader("🥤 Bebidas e Extras")
                        c_be_e1, c_be_e2 = st.columns(2)
                        with c_be_e1:
                            e_refri_sn = st.selectbox("Refris?", ["Não", "Sim"], index=0 if ev.get("refri_sn")=="Sim" else 1, key=f"e_refri_sn_{ev_id}")
                            e_refri_marca = st.text_input("Marca Refri", value=ev.get("refri_marca",""), key=f"e_refri_m_{ev_id}")
                            e_refri_val = st.number_input("Valor Refri", value=float(ev.get("refri_val",0) or 0), key=f"e_refri_v_{ev_id}")

                            e_aguag_sn = st.selectbox("Água Gás Barril?", ["Não", "Sim"], index=0 if ev.get("aguag_sn")=="Sim" else 1, key=f"e_aguag_sn_{ev_id}")
                            e_aguag_marca = st.text_input("Marca Água Gás", value=ev.get("aguag_marca",""), key=f"e_aguag_m_{ev_id}")
                            e_aguag_val = st.number_input("Valor Água Gás", value=float(ev.get("aguag_val",0) or 0), key=f"e_aguag_v_{ev_id}")
                        with c_be_e2:
                            e_aguas_sn = st.selectbox("Água Sem Gás?", ["Não", "Sim"], index=0 if ev.get("aguas_sn")=="Sim" else 1, key=f"e_aguas_sn_{ev_id}")
                            e_aguas_marca = st.text_input("Marca Água Sem Gás", value=ev.get("aguas_marca",""), key=f"e_aguas_m_{ev_id}")
                            e_aguas_val = st.number_input("Valor Água Sem Gás", value=float(ev.get("aguas_val",0) or 0), key=f"e_aguas_v_{ev_id}")

                            e_suco_sn = st.selectbox("Suco Lata?", ["Não", "Sim"], index=0 if ev.get("suco_sn")=="Sim" else 1, key=f"e_suco_sn_{ev_id}")
                            e_suco_marca = st.text_input("Marca Suco", value=ev.get("suco_marca",""), key=f"e_suco_m_{ev_id}")
                            e_suco_val = st.number_input("Valor Suco", value=float(ev.get("suco_val",0) or 0), key=f"e_suco_v_{ev_id}")

                        st.markdown("---")
                        st.subheader("🛠️ Item Improvisado / Extra")
                        c_im1, c_im2, c_im3, c_im4 = st.columns(4)
                        with c_im1:
                            e_imp_desc = st.text_input("Descrição", value=ev.get("imp_desc",""), key=f"e_imp_desc_{ev_id}")
                        with c_im2:
                            e_imp_sn = st.selectbox("Item Extra?", ["Não", "Sim"], index=0 if ev.get("imp_sn")=="Sim" else 1, key=f"e_imp_sn_{ev_id}")
                        with c_im3:
                            e_imp_marca = st.text_input("Marca Extra", value=ev.get("imp_marca",""), key=f"e_imp_marca_{ev_id}")
                        with c_im4:
                            e_imp_val = st.number_input("Valor Extra", value=float(ev.get("imp_val",0) or 0), key=f"e_imp_val_{ev_id}")

                        st.markdown("---")
                        st.subheader("🍺 Barris de Chopp Cadastrados (30L ou 50L)")
                        barris_atuais = ev.get("barris", [])
                        b1_data = barris_atuais[0] if len(barris_atuais) > 0 else {"estilo": "Nenhum", "litros": 0, "valor_total": 0.0}
                        b2_data = barris_atuais[1] if len(barris_atuais) > 1 else {"estilo": "Nenhum", "litros": 0, "valor_total": 0.0}
                        b3_data = barris_atuais[2] if len(barris_atuais) > 2 else {"estilo": "Nenhum", "litros": 0, "valor_total": 0.0}
                        b4_data = barris_atuais[3] if len(barris_atuais) > 3 else {"estilo": "Nenhum", "litros": 0, "valor_total": 0.0}

                        opt_estilos = ["Nenhum"] + ESTILOS_CHOPP
                        opt_litros_cad = [0, 50, 30]

                        def get_idx_safe(lst, val):
                            try:
                                return lst.index(val)
                            except Exception:
                                return 0

                        col_eb1, col_eb2 = st.columns(2)
                        with col_eb1:
                            st.markdown("##### 🛢️ Barril 1")
                            e_est_1 = st.selectbox("Estilo 1", opt_estilos, index=get_idx_safe(opt_estilos, b1_data.get("estilo", "Nenhum")), key=f"ee1_{ev_id}")
                            e_lit_1 = st.selectbox("Tamanho 1 (Litros)", opt_litros_cad, index=get_idx_safe(opt_litros_cad, b1_data.get("litros", 0)), key=f"el1_{ev_id}")
                            e_val_1 = st.number_input("Valor 1 (R$)", value=float(b1_data.get("valor_total", 0.0) or 0), step=10.0, key=f"ev1_{ev_id}")

                            st.markdown("##### 🛢️ Barril 3")
                            e_est_3 = st.selectbox("Estilo 3", opt_estilos, index=get_idx_safe(opt_estilos, b3_data.get("estilo", "Nenhum")), key=f"ee3_{ev_id}")
                            e_lit_3 = st.selectbox("Tamanho 3 (Litros)", opt_litros_cad, index=get_idx_safe(opt_litros_cad, b3_data.get("litros", 0)), key=f"el3_{ev_id}")
                            e_val_3 = st.number_input("Valor 3 (R$)", value=float(b3_data.get("valor_total", 0.0) or 0), step=10.0, key=f"ev3_{ev_id}")

                        with col_eb2:
                            st.markdown("##### 🛢️ Barril 2")
                            e_est_2 = st.selectbox("Estilo 2", opt_estilos, index=get_idx_safe(opt_estilos, b2_data.get("estilo", "Nenhum")), key=f"ee2_{ev_id}")
                            e_lit_2 = st.selectbox("Tamanho 2 (Litros)", opt_litros_cad, index=get_idx_safe(opt_litros_cad, b2_data.get("litros", 0)), key=f"el2_{ev_id}")
                            e_val_2 = st.number_input("Valor 2 (R$)", value=float(b2_data.get("valor_total", 0.0) or 0), step=10.0, key=f"ev2_{ev_id}")

                            st.markdown("##### 🛢️ Barril 4")
                            e_est_4 = st.selectbox("Estilo 4", opt_estilos, index=get_idx_safe(opt_estilos, b4_data.get("estilo", "Nenhum")), key=f"ee4_{ev_id}")
                            e_lit_4 = st.selectbox("Tamanho 4 (Litros)", opt_litros_cad, index=get_idx_safe(opt_litros_cad, b4_data.get("litros", 0)), key=f"el4_{ev_id}")
                            e_val_4 = st.number_input("Valor 4 (R$)", value=float(b4_data.get("valor_total", 0.0) or 0), step=10.0, key=f"ev4_{ev_id}")

                        st.markdown("---")
                        st.subheader("🔄 Chopp Consignado (Extra)")
                        c_e_con1, c_e_con2, c_e_con3 = st.columns(3)
                        with c_e_con1:
                            idx_cons_sn = 0 if ev.get("chopp_cons_sn") == "Sim" else 1
                            e_chopp_cons_sn = st.selectbox("Deixou Consignado?", ["Não", "Sim"], index=idx_cons_sn, key=f"e_cons_sn_{ev_id}")
                        with c_e_con2:
                            e_chopp_cons_estilo = st.selectbox("Estilo Consignado", ["Nenhum"] + ESTILOS_CHOPP, index=get_idx_safe(["Nenhum"] + ESTILOS_CHOPP, ev.get("chopp_cons_estilo", "Nenhum")), key=f"e_cons_est_{ev_id}")
                        with c_e_con3:
                            e_chopp_cons_litros = st.selectbox("Volume Consignado", [0, 30, 50], index=get_idx_safe([0, 30, 50], ev.get("chopp_cons_litros", 0)), key=f"e_cons_lit_{ev_id}")

                        e_obs = st.text_area("Observações", value=ev.get("observacoes", ""), key=f"obs_{ev_id}")

                        btn_salvar_edicao = st.form_submit_button("💾 Salvar Alterações na Nuvem")
                        if btn_salvar_edicao:
                            if not e_cli.strip():
                                st.warning("⚠️ O nome do cliente é obrigatório.")
                            else:
                                try:
                                    nova_data_str = f"{int(e_ano)}-{int(e_mes):02d}-{int(e_dia):02d}"
                                    datetime.strptime(nova_data_str, "%Y-%m-%d")
                                except ValueError:
                                    st.error("⚠️ Data inválida.")
                                    st.stop()

                                novas_barris = []
                                for est, lit, val in [
                                    (e_est_1, e_lit_1, e_val_1),
                                    (e_est_2, e_lit_2, e_val_2),
                                    (e_est_3, e_lit_3, e_val_3),
                                    (e_est_4, e_lit_4, e_val_4),
                                ]:
                                    if est != "Nenhum" and lit > 0:
                                        novas_barris.append({"estilo": est, "litros": int(lit), "valor_total": float(val)})

                                for item in reservas:
                                    if item.get("id") == ev_id:
                                        item["cliente"] = e_cli
                                        item["telefone"] = e_tel
                                        item["documento"] = e_doc
                                        item["tipo_evento"] = e_tipo_evento
                                        item["date"] = nova_data_str
                                        item["turno"] = e_turno
                                        item["qtd_pessoas"] = int(e_qtd_pes)
                                        item["status"] = e_stat
                                        item["valor_locacao"] = float(e_vloc)
                                        item["valor_sinal"] = float(e_vsinal)
                                        item["valor_caucao"] = float(e_vcaucao)
                                        item["som_sn"] = e_som_sn
                                        item["valor_som"] = float(e_vsom)
                                        item["retro_sn"] = e_retro_sn
                                        item["valor_retroprojetor"] = float(e_vretro)
                                        item["cuidador_sn"] = e_cuid_sn
                                        item["valor_taxa_adicional"] = float(e_vtaxa_adicional)
                                        item["refri_sn"] = e_refri_sn
                                        item["refri_marca"] = e_refri_marca
                                        item["refri_val"] = float(e_refri_val)
                                        item["agug_sn"] = aguag_sn  # mantem compatibilidade
                                        item["aguag_sn"] = e_aguag_sn
                                        item["aguag_marca"] = e_aguag_marca
                                        item["aguag_val"] = float(e_aguag_val)
                                        item["aguas_sn"] = e_aguas_sn
                                        item["aguas_marca"] = e_aguas_marca
                                        item["aguas_val"] = float(e_aguas_val)
                                        item["suco_sn"] = e_suco_sn
                                        item["suco_marca"] = e_suco_marca
                                        item["suco_val"] = float(e_suco_val)
                                        item["imp_desc"] = e_imp_desc
                                        item["imp_sn"] = e_imp_sn
                                        item["imp_marca"] = e_imp_marca
                                        item["imp_val"] = float(e_imp_val)
                                        item["barris"] = novas_barris
                                        item["chopp_cons_sn"] = e_chopp_cons_sn
                                        item["chopp_cons_estilo"] = e_chopp_cons_estilo
                                        item["chopp_cons_litros"] = int(e_chopp_cons_litros)
                                        item["observacoes"] = e_obs
                                        break

                                if salvar_dados_nuvem(reservas):
                                    st.session_state[f"edit_mode_{ev_id}"] = False
                                    st.success("✅ Alterações e data salvas com sucesso!")
                                    st.rerun()
    else:
        st.info("Nenhuma locação cadastrada para exibir.")
