
# 🧾 API de Alíquotas ICMS Interestadual (Docker)

API REST para consulta e cálculo de alíquotas de ICMS interestaduais e internas dos estados brasileiros,  **empacotada para execução em Docker** , pronta para ambientes de desenvolvimento, homologação ou produção.

> 🔎  **Importante** : Esta versão  **não depende de execução local via `python api.py`** . A aplicação roda em contêiner, expondo a API por porta configurável e utilizando variáveis de ambiente.

---

## 🎯 Sobre o Projeto

Esta API fornece acesso programático às alíquotas de ICMS interestaduais e internas dos 27 estados brasileiros. O sistema realiza web scraping de fontes oficiais, armazena os dados no Supabase e disponibiliza endpoints REST para consultas e cálculos.

A aplicação é distribuída como  **imagem Docker** , permitindo execução consistente em qualquer ambiente compatível com Docker.

---

## ✨ Funcionalidades

* ✅ Consulta de alíquotas interestaduais entre estados
* ✅ Consulta de alíquotas internas por estado
* ✅ Cálculo automático do valor do ICMS
* ✅ Cálculo do DIFAL
* ✅ Web scraping automatizado
* ✅ Persistência em Supabase (PostgreSQL)
* ✅ API RESTful (JSON)
* ✅ Health check
* ✅ Pronta para cloud, VPS ou Kubernetes

---

## 🛠️ Tecnologias Utilizadas

### Backend

* Python 3.10
* Flask
* Gunicorn
* Flask-CORS
* Selenium
* Supabase (PostgreSQL)
* python-dotenv

### Infraestrutura

* Docker
* Docker Compose

---

## 📦 Pré-requisitos

* Docker **20+**
* Docker Compose **v2+**
* Conta no Supabase

> ❌ Não é necessário Python instalado na máquina host

---

## 📁 Estrutura do Projeto

```
api-icms/
├── api.py
├── icms_scraper.py
├── database.py
├── config.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env
└── icms_interestadual.json
```

---

## 🐳 Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "-b", "0.0.0.0:5001", "api:app"]
```

---

## 🧩 docker-compose.yml

```yaml
services:
  api-icms:
    build: .
    container_name: api-icms
    ports:
      - "5001:5001"
    env_file:
      - .env
    restart: unless-stopped
```

---

## ⚙️ Configuração

### Variáveis de Ambiente (.env)

```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=chave_publica_aqui
FLASK_ENV=production
FLASK_PORT=5001
```

> 🔐 Em produção, utilize secrets do Docker ou do provedor cloud.

---

## 🚀 Executando com Docker

```bash
docker compose build
docker compose up -d
```

Ver logs:

```bash
docker logs -f api-icms
```

---

## 🌐 Acesso à API

* Local: `http://localhost:5001`
* Produção: `https://api.seudominio.com`

---

## 📡 Endpoints

### Health Check

```http
GET /health
```

### Consultar Alíquota

```http
GET /aliquota?origem=SC&destino=SP
```

### Calcular ICMS

```http
POST /calcular-icms
```

```json
{
  "origem": "SC",
  "destino": "SP",
  "valor_operacao": 1000
}
```

---

## 🔄 Scraping e Importação

Executar scraping dentro do contêiner:

```bash
docker exec -it api-icms python icms_scraper.py
```

---

## 🔌 Exemplos de Implementação

### 🐘 Laravel 12

**.env**

```env
ICMS_API_URL=https://api.seudominio.com
```

**Service**

```php
class IcmsService
{
    public function calcular(string $origem, string $destino, float $valor)
    {
        return Http::post(config('services.icms.url').'/calcular-icms', [
            'origem' => $origem,
            'destino' => $destino,
            'valor_operacao' => $valor
        ])->json();
    }
}
```

---

### 🟢 Vue 3

```js
axios.post('/calcular-icms', {
  origem: 'SC',
  destino: 'SP',
  valor_operacao: 1000
})
```

---

## 🧠 Arquitetura Recomendada

```
Vue 3 ─▶ Laravel 12 ─▶ API ICMS (Docker)
```

---

## ☁️ Deploy

Compatível com:

* VPS
* AWS ECS / EC2
* Google Cloud Run
* Azure Container Apps
* Kubernetes

Recomendado:

* Nginx / Traefik
* HTTPS (Let's Encrypt)
* Secrets

---

## 🐛 Troubleshooting

```bash
docker ps
docker logs api-icms
```

---

## 📄 Licença

MIT

---

## 👨‍💻 Autor

**Vinicius Rossini Costa**

---

⭐ Se este projeto foi útil, deixe uma estrela no repositório.
