import os
import csv
import io
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import database
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from urllib.parse import quote

app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='templates')

database.init_db()
database.seed_sample_data_if_empty()

def get_public_host():
    configs = database.get_configuracoes()
    dominio_custom = configs.get('dominio_publico', '').strip()
    if dominio_custom:
        return dominio_custom.rstrip('/')
        
    forwarded_host = request.headers.get('X-Forwarded-Host')
    if forwarded_host:
        return f"https://{forwarded_host}"
        
    if os.environ.get("VERCEL"):
        return f"https://{request.host}"
        
    return request.host_url.rstrip('/')

@app.route('/')
def index():
    return redirect(url_for('admin'))

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/atualizar/<token>')
def customer_portal(token):
    mensalista = database.get_mensalista_by_token(token)
    if not mensalista:
        return render_template('error.html', mensagem="Link de atualização inválido ou expirado."), 404
    return render_template('customer.html', mensalista=mensalista)

@app.route('/sucesso')
def success_page():
    return render_template('success.html')

# ==================== API ENDPOINTS ==================== #

@app.route('/api/mensalistas', methods=['GET'])
def api_get_mensalistas():
    mensalistas = database.get_all_mensalistas()
    host_url = get_public_host()
    
    for m in mensalistas:
        m['link_atualizacao'] = f"{host_url}/atualizar/{m['token']}"
        configs = database.get_configuracoes()
        msg_template = configs.get('mensagem_template', 'Olá {nome}, atualize seu cadastro: {link}')
        nome_estacionamento = configs.get('nome_estacionamento', 'Estacionamento WPS')
        
        msg_personalizada = msg_template.replace('{nome}', m['nome'])\
                                        .replace('{link}', m['link_atualizacao'])\
                                        .replace('{nome_estacionamento}', nome_estacionamento)
                                        
        m['mensagem_pronta'] = msg_personalizada
        m['whatsapp_url'] = f"https://api.whatsapp.com/send?phone={m['telefone']}&text={quote(msg_personalizada)}"
        
    return jsonify(mensalistas)

@app.route('/api/mensalistas', methods=['POST'])
def api_add_mensalista():
    data = request.json or {}
    nome = data.get('nome', '').strip()
    telefone = data.get('telefone', '').strip()
    numero_cartao = data.get('numero_cartao', '').strip()
    tipo_vinculo = data.get('tipo_vinculo', 'Lojista / Funcionário').strip()
    nome_loja = data.get('nome_loja', '').strip()
    cpf = data.get('cpf', '').strip()
    email = data.get('email', '').strip()
    
    if not nome or not telefone:
        return jsonify({'error': 'Nome e telefone são obrigatórios.'}), 400
        
    m_id = database.add_mensalista(
        nome, telefone, 
        numero_cartao=numero_cartao, 
        tipo_vinculo=tipo_vinculo, 
        nome_loja=nome_loja,
        cpf=cpf,
        email=email
    )
    return jsonify({'success': True, 'id': m_id}), 201

@app.route('/api/mensalistas/<int:m_id>', methods=['DELETE'])
def api_delete_mensalista(m_id):
    database.delete_mensalista(m_id)
    return jsonify({'success': True})

@app.route('/api/importar-csv', methods=['POST'])
def api_import_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado.'}), 400
        
    file = request.files['file']
    filename = file.filename.lower()
    
    records = []
    
    try:
        if filename.endswith('.csv') or filename.endswith('.txt'):
            raw_bytes = file.stream.read()
            text = ""
            for encoding in ['utf-8-sig', 'utf-8', 'latin1', 'cp1252', 'iso-8859-1']:
                try:
                    text = raw_bytes.decode(encoding)
                    break
                except Exception:
                    pass
                    
            delimiter = ',' if ',' in text else (';' if ';' in text else '\t')
            stream = io.StringIO(text, newline=None)
            csv_input = csv.reader(stream, delimiter=delimiter, skipinitialspace=True)
            
            headers = next(csv_input, None)
            
            for row in csv_input:
                if row and len(row) >= 2:
                    nome = str(row[0]).strip()
                    telefone = str(row[1]).strip()
                    numero_cartao = str(row[2]).strip() if len(row) >= 3 and row[2] else None
                    nome_loja = str(row[3]).strip() if len(row) >= 4 and row[3] else None
                    cpf = str(row[4]).strip() if len(row) >= 5 and row[4] else None
                    email = str(row[5]).strip() if len(row) >= 6 and row[5] else None
                    tipo_vinculo = "Mensalista Externo" if (nome_loja and "externo" in nome_loja.lower()) else "Lojista / Funcionário"
                    
                    if nome and telefone and not nome.lower().startswith('nome') and not nome.lower().startswith('mensalista'):
                        records.append({
                            'nome': nome,
                            'telefone': telefone,
                            'numero_cartao': numero_cartao,
                            'tipo_vinculo': tipo_vinculo,
                            'nome_loja': nome_loja,
                            'cpf': cpf,
                            'email': email
                        })
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if row and len(row) >= 2 and row[0] and row[1]:
                    nome = str(row[0]).strip()
                    telefone = str(row[1]).strip()
                    numero_cartao = str(row[2]).strip() if len(row) >= 3 and row[2] else None
                    nome_loja = str(row[3]).strip() if len(row) >= 4 and row[3] else None
                    cpf = str(row[4]).strip() if len(row) >= 5 and row[4] else None
                    email = str(row[5]).strip() if len(row) >= 6 and row[5] else None
                    tipo_vinculo = "Mensalista Externo" if (nome_loja and "externo" in nome_loja.lower()) else "Lojista / Funcionário"
                    
                    if nome and telefone and not nome.lower().startswith('nome') and not nome.lower().startswith('mensalista'):
                        records.append({
                            'nome': nome,
                            'telefone': telefone,
                            'numero_cartao': numero_cartao,
                            'tipo_vinculo': tipo_vinculo,
                            'nome_loja': nome_loja,
                            'cpf': cpf,
                            'email': email
                        })
        else:
            return jsonify({'error': 'Formato não suportado. Envie CSV ou Excel (.xlsx).'}), 400
            
        importados = database.add_mensalistas_bulk(records)
        return jsonify({'success': True, 'importados': importados, 'total_encontrados': len(records)})
    except Exception as e:
        return jsonify({'error': f"Erro ao processar arquivo: {str(e)}"}), 500

@app.route('/api/configuracoes', methods=['GET', 'POST'])
def api_configuracoes():
    if request.method == 'GET':
        return jsonify(database.get_configuracoes())
    else:
        data = request.json or {}
        for k, v in data.items():
            database.set_configuracao(k, str(v))
        return jsonify({'success': True})

@app.route('/api/token/<token>', methods=['GET'])
def api_get_token(token):
    mensalista = database.get_mensalista_by_token(token)
    if not mensalista:
        return jsonify({'error': 'Token inválido'}), 404
    return jsonify(mensalista)

@app.route('/api/recadastro/<token>', methods=['POST'])
def api_post_recadastro(token):
    data = request.json or {}
    veiculos = data.get('veiculos', [])
    numero_cartao = data.get('numero_cartao', '').strip()
    tipo_vinculo = data.get('tipo_vinculo', 'Lojista / Funcionário').strip()
    nome_loja = data.get('nome_loja', '').strip()
    cpf = data.get('cpf', '').strip()
    email = data.get('email', '').strip()
    
    if tipo_vinculo == 'Mensalista Externo':
        nome_loja = 'Mensalista Externo'
    elif not nome_loja:
        return jsonify({'error': 'Por favor, informe o nome ou número da sua loja/empresa.'}), 400
        
    if not numero_cartao or len(numero_cartao) != 6 or not numero_cartao.isdigit():
        return jsonify({'error': 'Por favor, informe o número do cartão de 6 dígitos.'}), 400

    if not veiculos or not isinstance(veiculos, list):
        return jsonify({'error': 'Informe ao menos 1 veículo com Modelo e Placa.'}), 400
        
    success, msg = database.update_mensalista_veiculos(
        token, veiculos, 
        numero_cartao=numero_cartao, 
        tipo_vinculo=tipo_vinculo, 
        nome_loja=nome_loja,
        cpf=cpf,
        email=email
    )
    if not success:
        return jsonify({'error': msg}), 400
        
    return jsonify({'success': True, 'mensagem': msg})

@app.route('/api/marcar-enviado/<int:m_id>', methods=['POST'])
def api_marcar_enviado(m_id):
    database.update_status_envio(m_id, 'Enviado')
    return jsonify({'success': True})

@app.route('/api/exportar-mensalistas', methods=['GET'])
def api_exportar_mensalistas():
    mensalistas = database.get_all_mensalistas()
    host_url = get_public_host()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lista de Mensalistas"
    
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    
    headers = [
        "ID", "Nome do Mensalista", "CPF", "E-mail", "Tipo de Vínculo", "Loja / Empresa", "Nº Cartão NEPOS", "Telefone",
        "Modelo Veículo", "Ano", "Cor", "Placa Liberada (LPR)", "Status Envio", "Status Recadastro", "Data Atualização", "Link Recadastro"
    ]
    
    ws.append(headers)
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = align_center
        
    row_count = 2
    for m in mensalistas:
        link = f"{host_url}/atualizar/{m['token']}"
        veiculos = m.get('veiculos', [])
        cartao = m.get('numero_cartao') or 'Pendente'
        vinculo = m.get('tipo_vinculo') or 'Lojista / Funcionário'
        loja = m.get('nome_loja') or '-'
        cpf = m.get('cpf') or '-'
        email = m.get('email') or '-'
        
        if veiculos:
            for v in veiculos:
                ws.append([
                    m['id'],
                    m['nome'],
                    cpf,
                    email,
                    vinculo,
                    loja,
                    cartao,
                    m['telefone'],
                    v.get('modelo', '-'),
                    v.get('ano', '-'),
                    v.get('cor', '-'),
                    v.get('placa', '-'),
                    m['status_envio'],
                    m['status_cadastro'],
                    m['data_atualizacao'] or '-',
                    link
                ])
                for col_num in range(1, 17):
                    cell = ws.cell(row=row_count, column=col_num)
                    cell.border = thin_border
                    cell.alignment = align_center if col_num in [1, 3, 5, 7, 8, 10, 12, 13, 14, 15] else align_left
                row_count += 1
        else:
            ws.append([
                m['id'],
                m['nome'],
                cpf,
                email,
                vinculo,
                loja,
                cartao,
                m['telefone'],
                "-",
                "-",
                "-",
                "-",
                m['status_envio'],
                m['status_cadastro'],
                m['data_atualizacao'] or '-',
                link
            ])
            for col_num in range(1, 17):
                cell = ws.cell(row=row_count, column=col_num)
                cell.border = thin_border
                cell.alignment = align_center if col_num in [1, 3, 5, 7, 8, 10, 12, 13, 14, 15] else align_left
            row_count += 1
            
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)
        
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"Mensalistas_Iguatemi_{timestamp}.xlsx"
    )

@app.route('/api/exportar-wps', methods=['GET'])
def api_exportar_wps():
    mensalistas = database.get_all_mensalistas()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cadastro Veiculos WPS"
    
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    
    headers = [
        "ID Mensalista", "Nome do Mensalista", "CPF", "E-mail", "Tipo Vínculo", "Loja / Empresa", "Nº Cartão NEPOS (6 dígitos)", "Telefone/WhatsApp",
        "Modelo do Veículo", "Ano", "Cor", "Placa Liberada (LPR)", "Data Recadastro"
    ]
    
    ws.append(headers)
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = align_center
        
    row_count = 2
    for m in mensalistas:
        veiculos = m.get('veiculos', [])
        cartao = m.get('numero_cartao') or 'Pendente'
        vinculo = m.get('tipo_vinculo') or 'Lojista / Funcionário'
        loja = m.get('nome_loja') or '-'
        cpf = m.get('cpf') or '-'
        email = m.get('email') or '-'
        
        if veiculos:
            for v in veiculos:
                ws.append([
                    m['id'],
                    m['nome'],
                    cpf,
                    email,
                    vinculo,
                    loja,
                    cartao,
                    m['telefone'],
                    v['modelo'],
                    v['ano'],
                    v['cor'],
                    v['placa'],
                    m['data_atualizacao'] or 'Pendente'
                ])
                for col_num in range(1, 14):
                    cell = ws.cell(row=row_count, column=col_num)
                    cell.border = thin_border
                    cell.alignment = align_center if col_num in [1, 3, 5, 7, 8, 10, 12, 13] else align_left
                row_count += 1
        else:
            ws.append([
                m['id'],
                m['nome'],
                cpf,
                email,
                vinculo,
                loja,
                cartao,
                m['telefone'],
                "Pendente de Recadastro",
                "-",
                "-",
                "-",
                "Pendente"
            ])
            for col_num in range(1, 14):
                cell = ws.cell(row=row_count, column=col_num)
                cell.border = thin_border
                cell.alignment = align_center if col_num in [1, 3, 5, 7, 8, 10, 12, 13] else align_left
            row_count += 1
            
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)
        
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"Relatorio_Veiculos_WPS_{timestamp}.xlsx"
    )

if __name__ == '__main__':
    print("Iniciando servidor MSGWHATS na porta 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)
