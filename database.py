import sqlite3
import secrets
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime

if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/msgwhats.db"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "msgwhats.db")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip('/')
SUPABASE_KEY = (
    os.environ.get("SUPABASE_KEY", "") or 
    os.environ.get("SUPABASE_PUBLISHABLE_KEY", "") or 
    os.environ.get("SUPABASE_ANON_KEY", "")
)

def is_supabase_enabled():
    return bool(SUPABASE_URL and SUPABASE_KEY)

def supabase_request(endpoint, method="GET", data=None, params=None, headers_extra=None):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
        
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    if headers_extra:
        headers.update(headers_extra)
        
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else True
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8", errors="ignore")
        print(f"Erro HTTP Supabase ({endpoint}): Status {e.code} - {err_content}")
        return None
    except Exception as e:
        print(f"Erro na requisição Supabase ({endpoint}):", e)
        return None

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if is_supabase_enabled():
        print("Conectado ao Supabase PostgreSQL na nuvem!")
        return
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mensalistas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            numero_cartao TEXT,
            tipo_vinculo TEXT DEFAULT 'Lojista / Funcionário',
            nome_loja TEXT,
            cpf TEXT,
            email TEXT,
            status_envio TEXT DEFAULT 'Pendente',
            data_envio TEXT,
            status_cadastro TEXT DEFAULT 'Pendente',
            data_atualizacao TEXT,
            observacoes TEXT
        )
    ''')
    
    for col, col_type in [("numero_cartao", "TEXT"), ("tipo_vinculo", "TEXT DEFAULT 'Lojista / Funcionário'"), ("nome_loja", "TEXT"), ("cpf", "TEXT"), ("email", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE mensalistas ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensalista_id INTEGER NOT NULL,
            modelo TEXT NOT NULL,
            ano TEXT NOT NULL,
            cor TEXT NOT NULL,
            placa TEXT NOT NULL,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mensalista_id) REFERENCES mensalistas (id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES 
        ('nome_estacionamento', 'Estacionamento Iguatemi Brasília'),
        ('dominio_publico', 'https://msgwhats.vercel.app'),
        ('mensagem_template', 'Olá {nome}, tudo bem?\n\nEstamos migrando nosso sistema de controle do estacionamento para leitura de placas! 🚗✨\n\nPara garantir seu acesso sem interrupções, por favor informe seu CPF, e-mail, número do cartão e veículos cadastrados no link abaixo:\n\n👉 {link}\n\nObrigado!'),
        ('intervalo_envio_segundos', '10')
    ''')
    
    conn.commit()
    conn.close()

def generate_token():
    return secrets.token_urlsafe(12)

def seed_sample_data_if_empty():
    if is_supabase_enabled():
        return
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM mensalistas")
    count = cursor.fetchone()[0]
    
    if count == 0:
        sample_mensalistas = [
            ("Carlos Eduardo Silva", "5511999887766", "123456", "Lojista / Funcionário", "Lojas Renner", "111.222.333-44", "carlos@email.com"),
            ("Mariana Souza Santos", "5511988776655", "654321", "Lojista / Funcionário", "Zara", "222.333.444-55", "mariana@email.com"),
            ("Roberto Almeida Costa", "5511977665544", "789012", "Mensalista Externo", "Mensalista Externo", "333.444.555-66", "roberto@email.com")
        ]
        
        for nome, telefone, cartao, vinculo, loja, cpf, email in sample_mensalistas:
            token = generate_token()
            cursor.execute(
                "INSERT INTO mensalistas (nome, telefone, token, numero_cartao, tipo_vinculo, nome_loja, cpf, email) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (nome, telefone, token, cartao, vinculo, loja, cpf, email)
            )
        
        cursor.execute("SELECT id FROM mensalistas LIMIT 1")
        m_id = cursor.fetchone()['id']
        cursor.execute(
            "INSERT INTO veiculos (mensalista_id, modelo, ano, cor, placa) VALUES (?, ?, ?, ?, ?)",
            (m_id, "Toyota Corolla", "2022", "Prata", "ABC1D23")
        )
        cursor.execute(
            "UPDATE mensalistas SET status_cadastro = 'Atualizado', data_atualizacao = ? WHERE id = ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), m_id)
        )
        
        conn.commit()
    conn.close()

def get_all_mensalistas():
    if is_supabase_enabled():
        joined = supabase_request("mensalistas", params={"select": "*,veiculos(*)", "order": "id.desc"})
        if isinstance(joined, list):
            for m in joined:
                if 'veiculos' not in m or m['veiculos'] is None:
                    m['veiculos'] = []
            return joined

        mensalistas = supabase_request("mensalistas", params={"select": "*", "order": "id.desc"}) or []
        veiculos = supabase_request("veiculos", params={"select": "*"}) or []
        
        veiculos_map = {}
        for v in veiculos:
            m_id = str(v.get('mensalista_id', ''))
            if m_id not in veiculos_map:
                veiculos_map[m_id] = []
            veiculos_map[m_id].append(v)
            
        for m in mensalistas:
            m_key = str(m.get('id', ''))
            m['veiculos'] = veiculos_map.get(m_key, [])
        return mensalistas

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mensalistas ORDER BY id DESC")
    mensalistas = [dict(row) for row in cursor.fetchall()]
    
    for m in mensalistas:
        cursor.execute("SELECT * FROM veiculos WHERE mensalista_id = ?", (m['id'],))
        m['veiculos'] = [dict(r) for r in cursor.fetchall()]
        
    conn.close()
    return mensalistas

def get_mensalista_by_token(token):
    if is_supabase_enabled():
        rows = supabase_request("mensalistas", params={"select": "*,veiculos(*)", "token": f"eq.{token}"})
        if not rows or len(rows) == 0:
            return None
        m = rows[0]
        if 'veiculos' not in m or m['veiculos'] is None:
            m['veiculos'] = []
        return m

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mensalistas WHERE token = ?", (token,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    mensalista = dict(row)
    cursor.execute("SELECT * FROM veiculos WHERE mensalista_id = ?", (mensalista['id'],))
    mensalista['veiculos'] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return mensalista

def add_mensalista(nome, telefone, numero_cartao=None, tipo_vinculo="Lojista / Funcionário", nome_loja=None, cpf=None, email=None):
    token = generate_token()
    telefone_clean = ''.join(c for c in str(telefone) if c.isdigit())
    if not telefone_clean.startswith('55') and len(telefone_clean) in [10, 11]:
        telefone_clean = '55' + telefone_clean

    if is_supabase_enabled():
        res = supabase_request("mensalistas", method="POST", data={
            "nome": nome,
            "telefone": telefone_clean,
            "token": token,
            "numero_cartao": numero_cartao,
            "tipo_vinculo": tipo_vinculo,
            "nome_loja": nome_loja,
            "cpf": cpf,
            "email": email
        })
        return res[0]['id'] if (res and isinstance(res, list) and len(res) > 0) else True

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO mensalistas (nome, telefone, token, numero_cartao, tipo_vinculo, nome_loja, cpf, email) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (nome, telefone_clean, token, numero_cartao, tipo_vinculo, nome_loja, cpf, email)
    )
    conn.commit()
    m_id = cursor.lastrowid
    conn.close()
    return m_id

def add_mensalistas_bulk(list_records):
    if not list_records:
        return 0
        
    records_to_insert = []
    for item in list_records:
        nome = item.get('nome', '').strip()
        telefone = str(item.get('telefone', '')).strip()
        telefone_clean = ''.join(c for c in telefone if c.isdigit())
        if not telefone_clean.startswith('55') and len(telefone_clean) in [10, 11]:
            telefone_clean = '55' + telefone_clean
            
        if nome and telefone_clean:
            records_to_insert.append({
                "nome": nome,
                "telefone": telefone_clean,
                "token": generate_token(),
                "numero_cartao": item.get('numero_cartao'),
                "tipo_vinculo": item.get('tipo_vinculo', 'Lojista / Funcionário'),
                "nome_loja": item.get('nome_loja'),
                "cpf": item.get('cpf'),
                "email": item.get('email')
            })
            
    if not records_to_insert:
        return 0
        
    if is_supabase_enabled():
        res = supabase_request("mensalistas", method="POST", data=records_to_insert)
        if res is not None:
            return len(records_to_insert)
        else:
            fallback_records = []
            for r in records_to_insert:
                fallback_records.append({
                    "nome": r["nome"],
                    "telefone": r["telefone"],
                    "token": r["token"]
                })
            res_fb = supabase_request("mensalistas", method="POST", data=fallback_records)
            return len(fallback_records) if res_fb is not None else 0

    conn = get_db_connection()
    cursor = conn.cursor()
    count = 0
    for r in records_to_insert:
        cursor.execute(
            "INSERT INTO mensalistas (nome, telefone, token, numero_cartao, tipo_vinculo, nome_loja, cpf, email) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (r['nome'], r['telefone'], r['token'], r['numero_cartao'], r['tipo_vinculo'], r['nome_loja'], r.get('cpf'), r.get('email'))
        )
        count += 1
    conn.commit()
    conn.close()
    return count

def update_mensalista_veiculos(token, list_veiculos, numero_cartao=None, tipo_vinculo=None, nome_loja=None, cpf=None, email=None):
    m = get_mensalista_by_token(token)
    if not m:
        return False, "Mensalista não encontrado"
        
    m_id = m['id']
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if is_supabase_enabled():
        supabase_request(f"veiculos?mensalista_id=eq.{m_id}", method="DELETE")
        
        for v in list_veiculos:
            modelo = v.get('modelo', '').strip()
            ano = str(v.get('ano', '')).strip()
            cor = v.get('cor', '').strip()
            placa = v.get('placa', '').strip().upper().replace('-', '').replace(' ', '')
            
            if modelo and placa:
                supabase_request("veiculos", method="POST", data={
                    "mensalista_id": m_id,
                    "modelo": modelo,
                    "ano": ano,
                    "cor": cor,
                    "placa": placa
                })
                
        patch_data = {
            "status_cadastro": "Atualizado",
            "data_atualizacao": now
        }
        if numero_cartao:
            patch_data["numero_cartao"] = str(numero_cartao).strip()
        if tipo_vinculo:
            patch_data["tipo_vinculo"] = tipo_vinculo
        if nome_loja is not None:
            patch_data["nome_loja"] = nome_loja.strip()
        if cpf:
            patch_data["cpf"] = str(cpf).strip()
        if email:
            patch_data["email"] = str(email).strip().lower()
            
        supabase_request(f"mensalistas?id=eq.{m_id}", method="PATCH", data=patch_data)
        return True, "Cadastro atualizado com sucesso!"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM veiculos WHERE mensalista_id = ?", (m_id,))
    
    for v in list_veiculos:
        modelo = v.get('modelo', '').strip()
        ano = str(v.get('ano', '')).strip()
        cor = v.get('cor', '').strip()
        placa = v.get('placa', '').strip().upper().replace('-', '').replace(' ', '')
        
        if modelo and placa:
            cursor.execute(
                "INSERT INTO veiculos (mensalista_id, modelo, ano, cor, placa, criado_em) VALUES (?, ?, ?, ?, ?, ?)",
                (m_id, modelo, ano, cor, placa, now)
            )
            
    cursor.execute(
        "UPDATE mensalistas SET status_cadastro = 'Atualizado', data_atualizacao = ?, numero_cartao = COALESCE(?, numero_cartao), tipo_vinculo = COALESCE(?, tipo_vinculo), nome_loja = COALESCE(?, nome_loja), cpf = COALESCE(?, cpf), email = COALESCE(?, email) WHERE id = ?",
        (now, numero_cartao, tipo_vinculo, nome_loja, cpf, email, m_id)
    )
    conn.commit()
    conn.close()
    return True, "Cadastro atualizado com sucesso!"

def update_status_envio(m_id, status):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == 'Enviado' else None
    
    if is_supabase_enabled():
        supabase_request(f"mensalistas?id=eq.{m_id}", method="PATCH", data={
            "status_envio": status,
            "data_envio": now
        })
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE mensalistas SET status_envio = ?, data_envio = COALESCE(?, data_envio) WHERE id = ?",
        (status, now, m_id)
    )
    conn.commit()
    conn.close()

def delete_mensalista(m_id):
    if is_supabase_enabled():
        supabase_request(f"mensalistas?id=eq.{m_id}", method="DELETE")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mensalistas WHERE id = ?", (m_id,))
    conn.commit()
    conn.close()

def get_configuracoes():
    if is_supabase_enabled():
        rows = supabase_request("configuracoes", params={"select": "*"}) or []
        return {row['chave']: row['valor'] for row in rows}

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chave, valor FROM configuracoes")
    rows = cursor.fetchall()
    conn.close()
    return {row['chave']: row['valor'] for row in rows}

def set_configuracao(chave, valor):
    if is_supabase_enabled():
        headers_upsert = {"Prefer": "resolution=merge-duplicates,return=representation"}
        res = supabase_request("configuracoes", method="POST", data={"chave": chave, "valor": valor}, headers_extra=headers_upsert)
        if res is None:
            encoded_chave = urllib.parse.quote(chave)
            supabase_request(f"configuracoes?chave=eq.{encoded_chave}", method="PATCH", data={"valor": valor})
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)",
        (chave, valor)
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    seed_sample_data_if_empty()
    print("Módulo de banco de dados híbrido ativado!")
