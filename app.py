import streamlit as st
from datetime import datetime
import time
import random
import pandas as pd
import os

st.set_page_config(page_title="Smart Production Control Room", layout="wide")

robos = ["XR-01", "XR-02", "XR-03", "XR-04", "XR-05"]
arquivo_csv = "eventos_producao.csv"
META_MENSAL = 12000
DIAS_UTEIS_MES = 22

if "producao" not in st.session_state:
    st.session_state.producao = {robo: 0 for robo in robos}

if "downtime" not in st.session_state:
    st.session_state.downtime = {robo: 0 for robo in robos}

if "historico_producao" not in st.session_state:
    st.session_state.historico_producao = pd.DataFrame(columns=["Horário"] + robos)

if "producao_diaria" not in st.session_state:
    st.session_state.producao_diaria = {dia: 0 for dia in range(1, DIAS_UTEIS_MES + 1)}

if "eventos" not in st.session_state:
    if os.path.exists(arquivo_csv):
        try:
            st.session_state.eventos = pd.read_csv(arquivo_csv, encoding="utf-8-sig").to_dict(orient="records")
        except Exception:
            st.session_state.eventos = []
    else:
        st.session_state.eventos = []

for robo in robos:
    if f"status_{robo}" not in st.session_state:
        st.session_state[f"status_{robo}"] = "Operando"

if "ultima_atualizacao" not in st.session_state:
    st.session_state.ultima_atualizacao = time.time()


def salvar_evento_csv(evento):
    pd.DataFrame([evento]).to_csv(
        arquivo_csv,
        mode="a",
        header=not os.path.exists(arquivo_csv),
        index=False,
        encoding="utf-8-sig"
    )


def existe_ocorrencia_aberta(robo):
    for evento in reversed(st.session_state.eventos):
        if evento["robo"] == robo:
            return evento.get("status_chamado") in ["Em atendimento", "Alarme Automático"]
    return False


def ultimo_evento_aberto(robo):
    for evento in reversed(st.session_state.eventos):
        if evento["robo"] == robo and evento.get("status_chamado") in ["Em atendimento", "Alarme Automático"]:
            return evento
    return None


def calcular_tempo_parado(data_hora):
    try:
        inicio = datetime.strptime(data_hora, "%d/%m/%Y %H:%M:%S")
        diff = datetime.now() - inicio
        total = int(diff.total_seconds())
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    except Exception:
        return "00:00:00"


def dia_util_atual():
    hoje = datetime.now()
    contador = 0

    for dia in range(1, hoje.day + 1):
        data = datetime(hoje.year, hoje.month, dia)
        if data.weekday() < 5:
            contador += 1

    return min(max(contador, 1), DIAS_UTEIS_MES)


# =========================
# SIMULADOR
# =========================
tempo_atual = time.time()
intervalo = tempo_atual - st.session_state.ultima_atualizacao

if intervalo >= 3:
    if random.random() < 0.05:
        robo_sorteado = random.choice(robos)

        if st.session_state[f"status_{robo_sorteado}"] == "Operando":
            motivos = [
                "Sensor de segurança acionado",
                "Temperatura elevada",
                "Falha mecânica",
                "Falha elétrica",
                "Falta de material"
            ]

            responsaveis = {
                "Sensor de segurança acionado": "Operação",
                "Temperatura elevada": "Manutenção mecânica",
                "Falha mecânica": "Manutenção mecânica",
                "Falha elétrica": "Manutenção elétrica",
                "Falta de material": "Logística"
            }

            motivo = random.choice(motivos)

            evento_auto = {
                "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "robo": robo_sorteado,
                "status": "Parado",
                "motivo": motivo,
                "responsavel": responsaveis[motivo],
                "status_chamado": "Alarme Automático",
                "tempo_parado": ""
            }

            st.session_state.eventos.append(evento_auto)
            salvar_evento_csv(evento_auto)
            st.session_state[f"status_{robo_sorteado}"] = "Parado"

    producao_ciclo = 0

    for robo in robos:
        status = st.session_state[f"status_{robo}"]

        if status == "Operando":
            incremento = random.randint(1, 4)
            st.session_state.producao[robo] += incremento
            producao_ciclo += incremento
        else:
            st.session_state.downtime[robo] += round(intervalo)

    dia_atual = dia_util_atual()
    st.session_state.producao_diaria[dia_atual] += producao_ciclo

    novo_ponto = {"Horário": datetime.now().strftime("%H:%M:%S")}
    for robo in robos:
        novo_ponto[robo] = st.session_state.producao[robo]

    st.session_state.historico_producao = pd.concat(
        [st.session_state.historico_producao, pd.DataFrame([novo_ponto])],
        ignore_index=True
    ).tail(15)

    st.session_state.ultima_atualizacao = tempo_atual
    st.rerun()


# =========================
# SIDEBAR GERENCIAL
# =========================
producao_mes = sum(st.session_state.producao_diaria.values())
percentual_meta = round((producao_mes / META_MENSAL) * 100, 1)

eventos_mes = pd.DataFrame(st.session_state.eventos)

total_paradas = 0
paradas_manutencao = 0
paradas_qualidade = 0
paradas_material = 0
paradas_seguranca = 0
paradas_outros = 0

if not eventos_mes.empty:
    eventos_parada = eventos_mes[eventos_mes["status"].astype(str) == "Parado"]
    total_paradas = len(eventos_parada)

    for motivo in eventos_parada["motivo"].astype(str):
        motivo_lower = motivo.lower()

        if "mecânica" in motivo_lower or "elétrica" in motivo_lower or "temperatura" in motivo_lower or "manutenção" in motivo_lower:
            paradas_manutencao += 1
        elif "qualidade" in motivo_lower:
            paradas_qualidade += 1
        elif "material" in motivo_lower:
            paradas_material += 1
        elif "segurança" in motivo_lower or "sensor" in motivo_lower:
            paradas_seguranca += 1
        else:
            paradas_outros += 1

st.sidebar.title("📅 Resumo Mensal")
st.sidebar.metric("🎯 Meta Mensal", f"{META_MENSAL:,}".replace(",", "."))
st.sidebar.metric("🏭 Produção Acumulada", f"{producao_mes:,}".replace(",", "."))
st.sidebar.metric("📈 Atingimento", f"{percentual_meta}%")
st.sidebar.progress(min(percentual_meta / 100, 1.0))

faltam_meta = max(META_MENSAL - producao_mes, 0)

st.sidebar.metric(
    "🎯 Faltam para Meta",
    f"{faltam_meta:,}".replace(",", ".")
)
st.sidebar.metric("📅 Dias Úteis", DIAS_UTEIS_MES)
st.sidebar.metric("🔴 Total de Paradas", total_paradas)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Paradas por Categoria")
st.sidebar.metric("🔧 Manutenção", paradas_manutencao)
st.sidebar.metric("✅ Qualidade", paradas_qualidade)
st.sidebar.metric("📦 Material", paradas_material)
st.sidebar.metric("🦺 Segurança", paradas_seguranca)
st.sidebar.metric("⚙️ Outros", paradas_outros)


# =========================
# INTERFACE PRINCIPAL
# =========================
st.title("🏭 Sala de Controle de Produção Inteligente")
st.subheader("Monitoramento em tempo real dos robôs XR")

operando = sum(1 for r in robos if st.session_state[f"status_{r}"] == "Operando")
parados = sum(1 for r in robos if st.session_state[f"status_{r}"] == "Parado")
manutencao = sum(1 for r in robos if st.session_state[f"status_{r}"] == "Manutenção")
producao_total = sum(st.session_state.producao.values())
eficiencia = round((operando / len(robos)) * 100, 1)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🏭 Produção Total", producao_total)
c2.metric("🟢 Operando", operando)
c3.metric("🔴 Parados", parados)
c4.metric("🟡 Manutenção", manutencao)
c5.metric("📈 Eficiência", f"{eficiencia}%")

st.markdown("---")

st.markdown("## 🚨 Ocorrências Ativas")

ocorrencias_ativas = []

for robo in robos:
    status = st.session_state[f"status_{robo}"]

    if status != "Operando":
        evento_aberto = ultimo_evento_aberto(robo)

        ocorrencias_ativas.append({
            "robo": robo,
            "status": status,
            "motivo": evento_aberto["motivo"] if evento_aberto else "Sem motivo registrado",
            "responsavel": evento_aberto["responsavel"] if evento_aberto else "Aguardando responsável",
            "data_hora": evento_aberto["data_hora"] if evento_aberto else datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        })

if ocorrencias_ativas:
    for evento in ocorrencias_ativas:
        c1, c2, c3, c4, c5, c6 = st.columns(6)

        c1.markdown(f"**Robô:** {evento['robo']}")
        c2.markdown(f"**Status:** {evento['status']}")
        c3.markdown(f"**Motivo:** {evento['motivo']}")
        c4.markdown(f"**Responsável:** {evento['responsavel']}")
        c5.markdown(f"**Parado há:** {calcular_tempo_parado(evento['data_hora'])}")

        with c6:
            if st.button(f"✅ Resolver {evento['robo']}", key=f"resolver_{evento['robo']}"):
                tempo_parado = calcular_tempo_parado(evento["data_hora"])

                evento_resolvido = {
                    "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "robo": evento["robo"],
                    "status": "Operando",
                    "motivo": "Retorno à Operação",
                    "responsavel": "Sistema",
                    "status_chamado": "Resolvido",
                    "tempo_parado": tempo_parado
                }

                st.session_state.eventos.append(evento_resolvido)
                salvar_evento_csv(evento_resolvido)
                st.session_state[f"status_{evento['robo']}"] = "Operando"
                st.success(f"{evento['robo']} liberado com sucesso!")
                time.sleep(0.3)
                st.rerun()

        st.divider()
else:
    st.success("✅ Nenhuma ocorrência ativa")

st.markdown("---")

g1, g2 = st.columns(2)

with g1:
    st.markdown("### 📊 Evolução da Produção por Robô")
    if not st.session_state.historico_producao.empty:
        st.line_chart(
            st.session_state.historico_producao.set_index("Horário"),
            use_container_width=True
        )
    else:
        st.info("Aguardando coleta de dados.")

with g2:
    st.markdown("### 📌 Paradas por Categoria")

    categorias = {
        "Manutenção": 0,
        "Qualidade": 0,
        "Material": 0,
        "Segurança": 0,
        "Outros": 0
    }

    for evento in st.session_state.eventos:
        motivo = str(evento["motivo"]).lower()

        if "manutenção" in motivo or "mecânica" in motivo or "elétrica" in motivo or "temperatura" in motivo:
            categorias["Manutenção"] += 1

        elif "qualidade" in motivo:
            categorias["Qualidade"] += 1

        elif "material" in motivo:
            categorias["Material"] += 1

        elif "sensor" in motivo or "segurança" in motivo:
            categorias["Segurança"] += 1

        else:
            categorias["Outros"] += 1

    df_categoria = pd.DataFrame(
        list(categorias.items()),
        columns=["Categoria", "Quantidade"]
    )

    df_categoria = df_categoria[
        df_categoria["Quantidade"] > 0
    ]

    if df_categoria.empty:
        st.info("Nenhuma parada categorizada ainda.")
    else:
        st.bar_chart(
            df_categoria.set_index("Categoria"),
            use_container_width=True
        )

st.markdown("---")

st.markdown("## 📅 Produção Diária do Mês")

df_diario = pd.DataFrame({
    "Dia Útil": list(st.session_state.producao_diaria.keys()),
    "Produção": list(st.session_state.producao_diaria.values())
})

st.bar_chart(df_diario.set_index("Dia Útil"), use_container_width=True)

st.markdown("---")
st.markdown("## 🏆 Ranking dos Robôs por Produção")

df_ranking = pd.DataFrame(
    list(st.session_state.producao.items()),
    columns=["Robô", "Produção"]
)

df_ranking = df_ranking.sort_values(
    by="Produção",
    ascending=False
)

st.dataframe(
    df_ranking,
    use_container_width=True,
    hide_index=True
)


st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("## 🤖 Status dos Robôs")

    cols = st.columns(5)

    for i, robo in enumerate(robos):
        status = st.session_state[f"status_{robo}"]

        cor = "🟢" if status == "Operando" else "🔴" if status == "Parado" else "🟡"

        cols[i].markdown(f"### {robo}")
        cols[i].markdown(f"{cor} **{status}**")
        cols[i].markdown(f"⬆️ {st.session_state.producao[robo]} peças")

with col2:
    st.markdown("## 🚨 Registrar Parada")

    robo_selecionado = st.selectbox("Robô", robos)

    motivo = st.selectbox(
        "Motivo da parada",
        [
            "Sensor de segurança acionado",
            "Falta de material",
            "Temperatura elevada",
            "Falha mecânica",
            "Falha elétrica",
            "Problema de qualidade",
            "Manutenção preventiva",
            "Outro problema de produção"
        ]
    )

    responsavel = st.selectbox(
        "Responsável acionado",
        [
            "Manutenção elétrica",
            "Manutenção mecânica",
            "Operação",
            "Qualidade",
            "Logística",
            "Produção"
        ]
    )

    if st.button("Registrar evento", use_container_width=True):
        if existe_ocorrencia_aberta(robo_selecionado):
            st.warning(f"{robo_selecionado} já possui uma ocorrência aberta.")
        else:
            novo_evento = {
                "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "robo": robo_selecionado,
                "status": "Parado",
                "motivo": motivo,
                "responsavel": responsavel,
                "status_chamado": "Em atendimento",
                "tempo_parado": ""
            }

            st.session_state.eventos.append(novo_evento)
            salvar_evento_csv(novo_evento)
            st.session_state[f"status_{robo_selecionado}"] = "Parado"

            st.success("Evento registrado com sucesso!")
            time.sleep(0.3)
            st.rerun()

st.markdown("---")

st.markdown("## 📋 Eventos Registrados")

if st.session_state.eventos:
    df_historico = pd.DataFrame(st.session_state.eventos)
    st.dataframe(df_historico, use_container_width=True)

    csv_download = df_historico.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="📄 Baixar relatório CSV",
        data=csv_download,
        file_name="relatorio_producao.csv",
        mime="text/csv"
    )
else:
    st.info("Nenhum evento registrado ainda.")