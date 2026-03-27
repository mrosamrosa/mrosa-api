# MROSA PDF Generator API

Serviço de geração de propostas comerciais em PDF com timbrado MROSA.

## Endpoint

### POST /gerar-proposta

**Body JSON:**
```json
{
  "cliente": "Nome do Cliente",
  "cidade": "São Paulo",
  "data": "27/03/2026",
  "numero_proposta": "001/2026",
  "items": [
    {"desc": "Produto A", "qtd": 2, "preco_unit": 150.00}
  ],
  "desconto": 0.10,
  "observacoes": "Pagamento em 30 dias."
}
```

**Resposta:**
```json
{
  "success": true,
  "pdf_base64": "base64encodedpdf..."
}
```

### GET /health
Verifica se o serviço está online.
