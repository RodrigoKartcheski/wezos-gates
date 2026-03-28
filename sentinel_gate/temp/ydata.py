from ydata_profiling import ProfileReport
import pandas as pd
from google.cloud import bigquery
from google.cloud import storage
import tempfile
import itertools
from datetime import date
import warnings # Importar warnings para lidar com o aviso do BigQuery
import json
import os
import shutil
import numpy as np

# Ignorar o aviso específico do BigQuery Storage (opcional, mas limpa a saída)
warnings.filterwarnings("ignore", message="BigQuery Storage module not found")

# Configuração do projeto e dados
config = {
    "project_id": "elet-dados-comercializacao-dev",
    "dataset_id": "ds_elet_comercializacao_refined_portfolio",
    "table_id": "tb_comercializacao_refined_sigc4e_mandatos_control",
    "checkNulls": ["*"], # Adicione aqui as colunas que deseja checar
    "checkMaxDate": ["dh_uploaded_at"], # Adicione aqui as colunas para ver a data máxima (suporta *)
    "checkDateGroups": ["*"], # Adicione aqui as colunas para ver a contagem por dia (suporta *)
    "checkConstantColumns": ["*"], # Detectar colunas com valor único
    "checkOutliers": ["*"], # Detectar valores fora do desvio padrão (numéricos)
    "checkEmptyStrings": ["*"] # Detectar strings vazias "" ou " "
}

project_id = config["project_id"]
dataset_id = config["dataset_id"]
table_id = config["table_id"]
check_nulls_cols = config.get("checkNulls", [])
check_max_date_cols = config.get("checkMaxDate", [])
check_date_groups_cols = config.get("checkDateGroups", [])
check_constant_cols = config.get("checkConstantColumns", [])
check_outlier_cols = config.get("checkOutliers", [])
check_empty_string_cols = config.get("checkEmptyStrings", [])

# Query e coleta de dados
client = bigquery.Client(project=project_id)
query = f"""
    SELECT * FROM `{project_id}.{dataset_id}.{table_id}`
    LIMIT 10000
"""
print("Executando query no BigQuery...")
df = client.query(query).to_dataframe()
print(f"DataFrame carregado com {len(df)} linhas.")

# Função para detectar chaves
def detectar_chaves(df):
    print("Detectando chaves baseadas em count distinct...")
    total_rows = len(df)
    print(f"Total de linhas no DataFrame: {total_rows}")
    
    # Calcular count distinct para todas as colunas
    distinct_counts = []
    
    colunas_ignoradas = ['dh_upload', 'dh_uploaded_at', 'uploaded_at']
    
    for col in df.columns:
        if col.lower() in colunas_ignoradas:
            print(f"Ignorando coluna de metadados {col} na detecção de chaves.")
            continue
            
        nunique = df[col].nunique(dropna=False) 
        distinct_counts.append({'coluna': col, 'distinct_count': nunique})
        
    # Ordenar pelos maiores resultados de distintos
    distinct_counts.sort(key=lambda x: x['distinct_count'], reverse=True)
    colunas_ordenadas = [item['coluna'] for item in distinct_counts]
    
    html = "<h2>Detecção de Chave Primária por Count Distinct</h2>"
    html += f"<p><strong>Total de colunas:</strong> {len(df.columns)}</p>"
    html += f"<p><strong>Total de registros analisados:</strong> {total_rows}</p>"
    
    html += "<h3>Contagem distinta por coluna (ordenado decrescente):</h3><ul>"
    for item in distinct_counts:
        html += f"<li><code>{item['coluna']}</code>: {item['distinct_count']} distintos</li>"
    html += "</ul>"
    
    primeira_col = colunas_ordenadas[0]
    primeira_qtd = distinct_counts[0]['distinct_count']
    
    # 1. Verifica se a primeira coluna (com maior cardinalidade) já é a chave
    if primeira_qtd == total_rows:
        html += f"<h3>✅ Chave Primária Encontrada!</h3>"
        html += f"<p>A coluna <code>{primeira_col}</code> possui unicidade total ({primeira_qtd} valores distintos, igual ao total de linhas).</p>"
        print(f"Chave primária encontrada na primeira coluna testada: {primeira_col}")
        return html
        
    # 2. Se não, combinar iterativamente a próxima coluna na ordem decrescente
    print("Nenhuma coluna única atinge a contagem total. Iniciando combinações concatenadas...")
    html += "<h3>Tentativas de Chave Composta (Concatenação):</h3><ul>"
    
    colunas_combinadas = [primeira_col]
    
    for i in range(1, len(colunas_ordenadas)):
        proxima_col = colunas_ordenadas[i]
        colunas_combinadas.append(proxima_col)
        
        subset = df[colunas_combinadas]
        distinct_combo = len(subset.drop_duplicates())
        
        combo_str = " + ".join(colunas_combinadas)
        html += f"<li>Combinação <code>{combo_str}</code>: {distinct_combo} distintos</li>"
        print(f"  Testando combinação: {combo_str} -> {distinct_combo} distintos")
        
        if distinct_combo == total_rows:
            html += "</ul>"
            html += f"<h3>✅ Chave Primária Composta Encontrada!</h3>"
            html += f"<p>A combinação <code>{combo_str}</code> possui unicidade total ({total_rows} valores distintos, igual ao total de linhas).</p>"
            print(f"Chave primária composta encontrada: {combo_str}")
            return html
            
    html += "</ul>"
    html += "<p><em>Nenhuma combinação iterativa atingiu a unicidade total de linhas.</em></p>"
    print("Nenhuma chave alcançou a contagem total.")
    return html

def verificar_nulos(df, colunas):
    # Filtrar nomes de colunas vazios ou apenas espaços
    colunas = [c for c in colunas if c and str(c).strip()]
    
    if not colunas or df.empty:
        return ""
    
    # Expandir o wildcard '*' para todas as colunas
    if "*" in colunas:
        colunas = df.columns.tolist()
    
    print(f"Verificando nulos para as colunas: {colunas}...")
    html = "<h2>Validação de Valores Nulos (checkNulls)</h2><ul>"
    
    for col in colunas:
        if col not in df.columns:
            html += f"<li>⚠️ Coluna <code>{col}</code> não encontrada no DataFrame.</li>"
            continue
            
        null_count = df[col].isnull().sum()
        if null_count > 0:
            html += f"<li>❌ Coluna <code>{col}</code>: Encontrados <strong>{null_count}</strong> valores nulos.</li>"
        else:
            html += f"<li>✅ Coluna <code>{col}</code>: Nenhum valor nulo encontrado.</li>"
            
    html += "</ul>"
    return html

def obter_data_maxima(df, colunas):
    # Filtrar nomes de colunas vazios ou apenas espaços
    colunas = [c for c in colunas if c and str(c).strip()]
    
    if not colunas or df.empty:
        return ""
    
    # Expandir o wildcard '*' para todas as colunas
    config_cols = colunas.copy()
    if "*" in colunas:
        colunas = df.columns.tolist()
        
    print(f"Obtendo datas máximas para as colunas: {colunas}...")
    html = "<h2>Validação de Datas Máximas (checkMaxDate)</h2><ul>"
    encontrou_data = False
    
    for col in colunas:
        if col not in df.columns:
            if "*" not in config_cols:
                html += f"<li>⚠️ Coluna <code>{col}</code> não encontrada no DataFrame.</li>"
            continue
            
        dtype = str(df[col].dtype)
        max_val = df[col].max()
        
        # Ignorar valores nulos para o máximo
        if pd.isna(max_val):
            if "*" not in config_cols:
                html += f"<li>ℹ️ Coluna <code>{col}</code>: Sem dados para calcular a data máxima.</li>"
            continue

        tipo_encontrado = None
        # Prioridade: Timestamp > Datetime > Date
        if "datetime64" in dtype:
            if "UTC" in dtype or (hasattr(df[col], 'dt') and df[col].dt.tz is not None):
                tipo_encontrado = "TIMESTAMP"
            else:
                tipo_encontrado = "DATETIME"
        elif isinstance(max_val, date):
            tipo_encontrado = "DATE"
            
        if tipo_encontrado:
            html += f"<li>📅 Coluna <code>{col}</code> ({tipo_encontrado}): Máximo em <strong>{max_val}</strong></li>"
            encontrou_data = True
        elif "*" not in config_cols:
             # Apenas mostra se foi explicitamente solicitado e não é data
             html += f"<li>⚠️ Coluna <code>{col}</code> não parece ser um tipo de data suportado ({dtype}).</li>"
             
    if not encontrou_data and "*" in config_cols:
        html += "<li>ℹ️ Nenhuma coluna de data encontrada automaticamente com <code>*</code>.</li>"
        
    html += "</ul>"
    return html

def verificar_distribuicao_datas(df, colunas):
    # Filtrar nomes de colunas vazios ou apenas espaços
    colunas = [c for c in colunas if c and str(c).strip()]
    
    if not colunas or df.empty:
        return ""
    
    # Expandir o wildcard '*' para todas as colunas
    config_cols = colunas.copy()
    if "*" in colunas:
        colunas = df.columns.tolist()
        
    print(f"Verificando distribuição por data para as colunas: {colunas}...")
    html = "<h2>Distribuição de Registros por Dia (checkDateGroups)</h2>"
    encontrou_data = False
    
    for col in colunas:
        if col not in df.columns:
            if "*" not in config_cols:
                html += f"<p>⚠️ Coluna <code>{col}</code> não encontrada.</p>"
            continue
            
        dtype = str(df[col].dtype)
        
        # Verificar se é tipo data/datetime
        is_date = "datetime64" in dtype or "date" in dtype.lower() or isinstance(df[col].dropna().iloc[0] if not df[col].dropna().empty else None, date)
        
        if not is_date:
            if "*" not in config_cols:
                html += f"<p>⚠️ Coluna <code>{col}</code> não é um tipo de data suportado.</p>"
            continue

        encontrou_data = True
        # Converter para data e contar
        counts = pd.to_datetime(df[col], errors='coerce').dt.date.value_counts().sort_index(ascending=False)
        
        html += f"<h3>Coluna: <code>{col}</code></h3>"
        html += "<table border='1' style='border-collapse: collapse; width: 300px; text-align: left;'>"
        html += "<tr style='background-color: #f2f2f2;'><th>Data</th><th>Registros</th></tr>"
        
        for dia, count in counts.items():
            html += f"<tr><td>{dia}</td><td>{count}</td></tr>"
            
        html += f"<tr><td style='font-weight: bold;'>TOTAL</td><td style='font-weight: bold;'>{counts.sum()}</td></tr>"
        html += "</table><br>"

    if not encontrou_data and "*" in config_cols:
        html += "<p><i>Nenhuma coluna de data encontrada para agrupamento.</i></p>"
        
    return html

def verificar_colunas_constantes(df, colunas):
    colunas = [c for c in colunas if c and str(c).strip()]
    if not colunas or df.empty:
        return ""
    
    if "*" in colunas:
        colunas = df.columns.tolist()
        
    print(f"Verificando colunas constantes: {colunas}...")
    html = "<h2>Colunas com Valores Constantes (checkConstantColumns)</h2><ul>"
    encontrou_constante = False
    
    for col in colunas:
        if col not in df.columns:
            continue
            
        unique_values = df[col].nunique(dropna=False)
        if unique_values == 1:
            valor = df[col].iloc[0]
            html += f"<li>⚠️ Coluna <code>{col}</code> possui valor único em todas as linhas: <strong>{valor}</strong></li>"
            encontrou_constante = True
            
    if not encontrou_constante:
        html += "<li>✅ Nenhuma coluna constante encontrada nas colunas analisadas.</li>"
        
    html += "</ul>"
    return html

def verificar_outliers(df, colunas):
    colunas = [c for c in colunas if c and str(c).strip()]
    if not colunas or df.empty:
        return ""
    
    if "*" in colunas:
        colunas = df.select_dtypes(include=['number']).columns.tolist()
        
    print(f"Verificando outliers (Z-Score > 3) para: {colunas}...")
    html = "<h2>Detecção de Outliers - Z-Score > 3 (checkOutliers)</h2>"
    encontrou_outlier_geral = False
    
    for col in colunas:
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue
            
        mean = df[col].mean()
        std = df[col].std()
        
        if std == 0: continue # Evita divisão por zero em colunas constantes
        
        # Identificar outliers (Z-score > 3)
        outliers = df[np.abs((df[col] - mean) / std) > 3][col]
        
        if not outliers.empty:
            encontrou_outlier_geral = True
            html += f"<h3>Coluna: <code>{col}</code></h3><ul>"
            html += f"<li>Média: {mean:.2f} | Desvio Padrão: {std:.2f}</li>"
            html += f"<li>❌ Encontrados <strong>{len(outliers)}</strong> valores suspeitos (Outliers).</li>"
            html += f"<li>Exemplos: {outliers.unique()[:5].tolist()}</li>"
            html += "</ul>"

    if not encontrou_outlier_geral:
        html += "<p>✅ Nenhum outlier estatístico detectado (Z-Score > 3).</p>"
        
    return html

def verificar_strings_vazias(df, colunas):
    colunas = [c for c in colunas if c and str(c).strip()]
    if not colunas or df.empty:
        return ""
    
    if "*" in colunas:
        colunas = df.select_dtypes(include=['object']).columns.tolist()
        
    print(f"Verificando strings vazias ou espaços para: {colunas}...")
    html = "<h2>Strings Vazias ou Espaços (checkEmptyStrings)</h2><ul>"
    encontrou_vazio = False
    
    for col in colunas:
        if col not in df.columns: continue
        
        # Filtra apenas o que é string de fato
        empty_count = df[col].apply(lambda x: isinstance(x, str) and not str(x).strip()).sum()
        
        if empty_count > 0:
            encontrou_vazio = True
            html += f"<li>❌ Coluna <code>{col}</code>: Encontradas <strong>{empty_count}</strong> strings vazias ou apenas espaços.</li>"
            
    if not encontrou_vazio:
        html += "<li>✅ Nenhuma string 'falsa vazia' encontrada.</li>"
        
    html += "</ul>"
    return html

html_keys = detectar_chaves(df)
html_nulls = verificar_nulos(df, check_nulls_cols)
html_max_date = obter_data_maxima(df, check_max_date_cols)
html_date_groups = verificar_distribuicao_datas(df, check_date_groups_cols)
html_const = verificar_colunas_constantes(df, check_constant_cols)
html_outliers = verificar_outliers(df, check_outlier_cols)
html_empty_str = verificar_strings_vazias(df, check_empty_string_cols)

html_custom = html_keys + html_nulls + html_max_date + html_date_groups + html_const + html_outliers + html_empty_str

# Geração do relatório de perfil
print("Gerando relatório ydata-profiling...")
profile = ProfileReport(
    df,
    title=f"Análise da Tabela {table_id}",
    explorative=True,
    minimal=False # Garante que mais seções sejam incluídas
)

# Salva o relatório em arquivo temporário
# Usar 'w+' para modo de escrita e leitura, e 'utf-8' para encoding
with tempfile.NamedTemporaryFile(mode='w+', suffix=".html", delete=False, encoding='utf-8') as tmpfile:
    html_path = tmpfile.name
    print(f"Salvando relatório em arquivo temporário: {html_path}")
    profile.to_file(html_path)
    print("Relatório salvo.")

# Abrir o arquivo HTML gerado e adicionar o HTML personalizado ao final
with open(html_path, 'a', encoding='utf-8') as file:
    file.write(html_custom)

# Opcional: salvar na pasta temp localmente em vez do GCS
os.makedirs("temp", exist_ok=True)
today = date.today().strftime("%Y-%m-%d")
destination_path = f"temp/relatorio_{table_id}_{today}.html"

shutil.move(html_path, destination_path)
print(f"Relatório gerado com sucesso e salvo em: {destination_path}")

print("Processo concluído.")
