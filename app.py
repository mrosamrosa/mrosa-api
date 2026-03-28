from flask import Flask, request, jsonify, send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
import io, os, base64
from datetime import datetime

app = Flask(__name__)

ZONE_X   = 71.0
ZONE_Y   = 203.9
ZONE_W   = 466.4
ZONE_H   = 477.9
ZONE_TOP = ZONE_Y + ZONE_H
PAD      = 18

DARK       = HexColor('#1a1a1a')
GRAY       = HexColor('#555555')
LIGHT_GRAY = HexColor('#888888')
BEIGE_BG   = HexColor('#F0ECE8')
W, H       = A4

def fmt_brl(val):
    return f"R$ {val:,.2f}".replace(',','X').replace('.',',').replace('X','.')

def gerar_pdf(dados):
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)

    c.setFillColor(BEIGE_BG)
    c.rect(ZONE_X, ZONE_Y, ZONE_W, ZONE_H, fill=1, stroke=0)

    y = ZONE_TOP - PAD

    cliente = dados.get('cliente', 'Cliente')
    num     = dados.get('numero_proposta', '')
    c.setFont('Helvetica-Bold', 11)
    c.setFillColor(DARK)
    c.drawString(ZONE_X + PAD, y, cliente)
    if num:
        c.setFont('Helvetica', 8)
        c.setFillColor(LIGHT_GRAY)
        c.drawRightString(ZONE_X + ZONE_W - PAD, y, f'Nº {num}')
    y -= 13

    cidade = dados.get('cidade', '')
    data   = dados.get('data', datetime.now().strftime('%d/%m/%Y'))
    c.setFont('Helvetica', 8)
    c.setFillColor(GRAY)
    c.drawString(ZONE_X + PAD, y, f'{cidade}  ·  {data}')
    y -= 10

    c.setStrokeColor(HexColor('#c8c3bc'))
    c.setLineWidth(0.4)
    c.line(ZONE_X + PAD, y, ZONE_X + ZONE_W - PAD, y)
    y -= 10

    c.setFont('Helvetica-Bold', 10)
    c.setFillColor(DARK)
    c.drawString(ZONE_X + PAD, y, 'PROPOSTA COMERCIAL')
    y -= 14

    obs = dados.get('observacoes', '')
    if obs:
        c.setFont('Helvetica-Oblique', 7.5)
        c.setFillColor(GRAY)
        max_w = ZONE_W - PAD * 2
        words = obs.split()
        line  = ''
        for word in words:
            test = (line + ' ' + word).strip()
            if c.stringWidth(test, 'Helvetica-Oblique', 7.5) < max_w:
                line = test
            else:
                c.drawString(ZONE_X + PAD, y, line)
                y -= 11
                line = word
        if line:
            c.drawString(ZONE_X + PAD, y, line)
            y -= 11
        y -= 4

    items = dados.get('items', [])
    if isinstance(items, str):
        import json as _json
        items = _json.loads(items)
    desconto_pct = float(dados.get('desconto', 0))
    subtotal     = sum(float(it['qtd']) * float(it['preco_unit']) for it in items)
    desconto_val = subtotal * desconto_pct
    total        = subtotal - desconto_val

    tw    = ZONE_W - PAD * 2
    col_w = [tw*0.48, tw*0.11, tw*0.205, tw*0.205]
    heads = ['Descrição', 'Qtd.', 'Valor Unit.', 'Subtotal']
    row_h = 18
    tx    = ZONE_X + PAD

    c.setFillColor(DARK)
    c.rect(tx, y - row_h, tw, row_h, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 7.5)
    xc = tx
    for i, (h, cw) in enumerate(zip(heads, col_w)):
        if i == 0: c.drawString(xc + 5, y - row_h + 6, h)
        else:      c.drawRightString(xc + cw - 4, y - row_h + 6, h)
        xc += cw
    y -= row_h

    for idx, item in enumerate(items):
        bg = HexColor('#e8e4df') if idx % 2 == 0 else BEIGE_BG
        c.setFillColor(bg)
        c.rect(tx, y - row_h, tw, row_h, fill=1, stroke=0)
        c.setStrokeColor(HexColor('#d5d0cb'))
        c.setLineWidth(0.3)
        c.line(tx, y, tx + tw, y)
        sub_item = float(item['qtd']) * float(item['preco_unit'])
        qtd_str  = str(item['qtd']).replace('.0','') if str(item['qtd']).endswith('.0') else str(item['qtd'])
        c.setFillColor(DARK)
        c.setFont('Helvetica', 7.5)
        vals = [item['desc'], qtd_str, fmt_brl(float(item['preco_unit'])), fmt_brl(sub_item)]
        xc = tx
        for i, (v, cw) in enumerate(zip(vals, col_w)):
            if i == 0: c.drawString(xc + 5, y - row_h + 6, str(v))
            else:      c.drawRightString(xc + cw - 4, y - row_h + 6, str(v))
            xc += cw
        y -= row_h

    c.setStrokeColor(HexColor('#c8c3bc'))
    c.setLineWidth(0.5)
    c.line(tx, y, tx + tw, y)
    y -= 10

    rx = ZONE_X + ZONE_W - PAD
    c.setFont('Helvetica', 8)
    c.setFillColor(GRAY)
    c.drawRightString(rx, y, f'Subtotal:  {fmt_brl(subtotal)}')
    y -= 12

    if desconto_pct > 0:
        c.setFont('Helvetica', 8)
        c.setFillColor(HexColor('#b03a2e'))
        c.drawRightString(rx, y, f'Desconto ({desconto_pct*100:.0f}%):  - {fmt_brl(desconto_val)}')
        y -= 12

    c.setFont('Helvetica-Bold', 10)
    c.setFillColor(DARK)
    c.drawRightString(rx, y, f'TOTAL:  {fmt_brl(total)}')
    tw_t = c.stringWidth(f'TOTAL:  {fmt_brl(total)}', 'Helvetica-Bold', 10)
    y -= 3
    c.setStrokeColor(DARK)
    c.setLineWidth(0.8)
    c.line(rx - tw_t, y, rx, y)
    y -= 14

    c.setFont('Helvetica-Oblique', 7)
    c.setFillColor(LIGHT_GRAY)
    c.drawString(ZONE_X + PAD, y, 'Esta proposta é válida por 15 dias corridos a partir da data de emissão.')

    bar_text = f'  {cidade.upper()}  —  {data}  ' * 6
    c.setFillColor(HexColor('#1a1a1a'))
    c.rect(0, 36, W, 34, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont('Helvetica', 7.5)
    c.drawString(15, 50, bar_text[:110])

    c.save()
    packet.seek(0)

    template = PdfReader('timbrado.pdf')
    overlay  = PdfReader(packet)
    writer   = PdfWriter()
    page     = template.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

@app.route('/gerar-proposta', methods=['POST'])
def gerar_proposta():
    try:
        import uuid, tempfile
        dados = request.get_json()

        pdf_bytes = gerar_pdf(dados)
        pdf_b64 = base64.b64encode(pdf_bytes.read()).decode('utf-8')

        filename = f"proposta_{uuid.uuid4().hex[:8]}.pdf"
        filepath = os.path.join(tempfile.gettempdir(), filename)
        pdf_bytes2 = gerar_pdf(dados)
        with open(filepath, 'wb') as f:
            f.write(pdf_bytes2.read())

        base_url = request.host_url.rstrip('/')
        pdf_url = f"{base_url}/pdf/{filename}"

        return jsonify({'success': True, 'pdf_base64': pdf_b64, 'pdf_url': pdf_url})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/pdf/<filename>', methods=['GET'])
def serve_pdf(filename):
    import tempfile
    filepath = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='application/pdf', as_attachment=True, download_name=filename)
    return jsonify({'error': 'File not found'}), 404

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'mrosa-pdf-generator'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
