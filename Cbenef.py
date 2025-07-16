import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import base64
from io import BytesIO

st.set_page_config(page_title="Crédito Presumido TTD SC", layout="wide")
st.title("📄 Conferência Crédito Presumido TTD - Ato DIAT 35/2024")

# Lista de NCMs específicos para aço/cobre
Aco_Cobre = {
    "74055000", "74031100", "74031200", "73043910", "73043110", "72253000", "72193500",
    "72193400", "72193300", "72193200", "74031300", "72192300", "72191400", "72191300",
    "72191200", "72142000", "72106100", "72091800", "74032900", "74050000", "74072110", 
    "74072120", "74081100", "72091700", "72091600", "74081900", "74091100", "74099000",
    "73251000", "73259910",
}

# Função para processar o XML
def processar_xml_conferencia(xml_content, cliente_simples, industria_10_icms):
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    root = ET.fromstring(xml_content)

    dados = []

    for det in root.findall('.//nfe:det', namespaces=ns):
        try:
            nItem = det.attrib.get('nItem', 'N/A')
            NCM = det.findtext('.//nfe:NCM', namespaces=ns) or 'N/A'
            pICMS = float(det.findtext('.//nfe:ICMS//nfe:pICMS', namespaces=ns) or 0.0)
            vICMS = float(det.findtext('.//nfe:ICMS//nfe:vICMS', namespaces=ns) or 0.0)
            vProd = float(det.findtext('.//nfe:vProd', namespaces=ns) or 0.0)
            vBC = float(det.findtext('.//nfe:ICMS//nfe:vBC', namespaces=ns) or 0.0)
            cBenef = det.findtext('.//nfe:prod/nfe:cBenef', namespaces=ns) or 'N/A'
            vCredPresumido_XML = float(det.findtext('.//nfe:prod/nfe:gCred/nfe:vCredPresumido', namespaces=ns) or 0.0)

            if vProd != vBC:
                if pICMS == 4.00:
                    perc_presumido_ttd = 1.0
                elif pICMS == 7.00:
                    perc_presumido_ttd = 3.4
                elif pICMS == 10.00:
                    perc_presumido_ttd = 3.6
                elif pICMS == 12.00:
                    perc_presumido_ttd = 2.1

                recalculo_cred_presumido = vICMS - (perc_presumido_ttd * vProd / 100)
            else:
                if pICMS == 4.00:
                    perc_presumido_ttd = 85.0 if NCM in Aco_Cobre else 75.0
                elif pICMS == 7.00:
                    perc_presumido_ttd = 70.0
                elif pICMS == 10.00 and industria_10_icms == "SIM":
                    perc_presumido_ttd = 90.0
                elif pICMS == 10.00:
                    perc_presumido_ttd = 64.0
                elif pICMS == 12.00:
                    perc_presumido_ttd = 70.0 if cliente_simples == "SIM" else 82.5

                recalculo_cred_presumido = vICMS * perc_presumido_ttd / 100

            diferenca = recalculo_cred_presumido - vCredPresumido_XML

            dados.append({
                'nItem': nItem,
                'NCM': NCM,
                'pICMS': round(pICMS, 2),
                'vICMS': round(vICMS, 2),
                'vProd': round(vProd, 2),
                'vBC': round(vBC, 2),
                'Perc Presumido TTD': round(perc_presumido_ttd, 2),
                'Recalculo Cred. Presumido': round(recalculo_cred_presumido, 2),
                'vCredPresumido XML': round(vCredPresumido_XML, 2),
                'Diferença': round(diferenca, 2),
                'Código cBENEF': cBenef
            })
        except Exception as e:
            st.warning(f"Erro ao processar item {nItem}: {e}")

    return pd.DataFrame(dados)

# Upload do XML
uploaded_file = st.file_uploader("📤 Importar Arquivo XML da NF-e", type=["xml"])
cliente_simples = st.radio("Cliente Optante pelo Simples Nacional?", ["NÃO", "SIM"], horizontal=True)
industria_10_icms = st.radio("Indústria / Carta Venda com Alíquota de ICMS 10%?", ["NÃO", "SIM"], horizontal=True)

# Processamento
if uploaded_file:
    xml_content = uploaded_file.read()
    df_resultado = processar_xml_conferencia(xml_content, cliente_simples, industria_10_icms)

    st.success("✅ XML processado com sucesso!")

    st.dataframe(df_resultado, use_container_width=True)

    # Exportação para Excel
    def gerar_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Resultado')
        output.seek(0)
        return output

    st.download_button(
        label="📥 Exportar para Excel",
        data=gerar_excel(df_resultado),
        file_name="credito_presumido.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("💡 Faça o upload de um arquivo XML para iniciar a conferência.")
