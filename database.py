import sqlite3
import secrets
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime

# No Vercel, o diretório raiz é somente leitura, então usa-se /tmp para o SQLite fallback
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

def supabase_request(endpoint, method="GET", data=None, params=None):
    """Executa requisições REST diretamente para o Supabase PostgreSQL."""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
        
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else True
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
            status_envio TEXT DEFAULT 'Pendente',
            data_envio TEXT,
            status_cadastro TEXT DEFAULT 'Pendente',
            data_atualizacao TEXT,
            observacoes TEXT
        )
    ''')
    
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
        ('nome_estacionamento', 'Estacionamento Central WPS'),
        ('mensagem_template', 'Olá {nome}, tudo bem?\n\nEstamos migrando nosso sistema de controle do estacionamento para leitura de placas! 🚗✨\n\nPara garantir seu acesso sem interrupções, por favor atualize os veículos cadastrados no link abaixo:\n\n👉 {link}\n\nObrigado!'),
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
            ("Carlos Eduardo Silva", "5511999887766"),
            ("Mariana Souza Santos", "5511988776655"),
            ("Roberto Almeida Costa", "5511977665544"),
            ("Fernanda Oliveira Lima", "5511966554433"),
            ("Ricardo Pereira Gomes", "5511955443322")
        ]
        
        for nome, telefone in sample_mensalistas:
            token = generate_token()
            cursor.execute(
                "INSERT INTO mensalistas (nome, telefone, token) VALUES (?, ?, ?)",
                (nome, telefone, token)
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

# API Operations with Supabase Cloud + SQLite Local Dual Support

def get_all_mensalistas():
    if is_supabase_enabled():
        mensalistas = supabase_request("mensalistas", params={"select": "*", "order": "id.desc"}) or []
        veiculos = supabase_request("veiculos", params={"select": "*"}) or []
        
        veiculos_map = {}
        for v in veiculos:
            m_id = v.get('mensalista_id')
            if m_id not in veiculos_map:
                veiculos_map[m_id] = []
            veiculos_map[m_id].append(v)
            
        for m in mensalistas:
            m['veiculos'] = veiculos_map.get(m['id'], [])
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
        rows = supabase_request("mensalistas", params={"select": "*", "token": f"eq.{token}"})
        if not rows or len(rows) == 0:
            return None
        m = rows[0]
        veiculos = supabase_request("veiculos", params={"select": "*", "mensalista_id": f"eq.{m['id']}"}) or []
        m['veiculos'] = veiculos
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

def add_mensalista(nome, telefone):
    token = generate_token()
    telefone_clean = ''.join(c for c in telefone if c.isdigit())
    if not telefone_clean.startswith('55') and len(telefone_clean) in [10, 11]:
        telefone_clean = '55' + telefone_clean

    if is_supabase_enabled():
        res = supabase_request("mensalistas", method="POST", data={
            "nome": nome,
            "telefone": telefone_clean,
            "token": token
        })
        return res[0]['id'] if res else None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO mensalistas (nome, telefone, token) VALUES (?, ?, ?)",
        (nome, telefone_clean, token)
    )
    conn.commit()
    m_id = cursor.lastrowid
    conn.close()
    return m_id

def update_mensalista_veiculos(token, list_veiculos):
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
                
        supabase_request(f"mensalistas?id=eq.{m_id}", method="PATCH", data={
            "status_cadastro": "Atualizado",
            "data_atualizacao": now
        })
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
        "UPDATE mensalistas SET status_cadastro = 'Atualizado', data_atualizacao = ? WHERE id = ?",
        (now, m_id)
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
        supabase_request("configuracoes", method="POST", data={"chave": chave, "valor": valor})
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
