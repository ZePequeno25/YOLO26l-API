# Guia de Inferencia Remota com SSL (Gateway Local -> Ubuntu com GPU)

Data: 2026-04-05  
Objetivo: manter a API atual como ponto de conexao e delegar apenas a predicao para um servidor Ubuntu com GPU NVIDIA.

---

## 1. Arquitetura recomendada

```text
Mobile/App Cliente
   |
   | HTTPS
   v
API Local (Windows) - Gateway
   |\
   | \- Firebase/Auth/Logs/Regras de negocio (continua local)
   |
   | HTTPS (SSL)
   v
API de Inferencia (Ubuntu + 3x 1080 Ti)
   |
   \- YOLO/CUDA retorna boxes, confianca, classes, contagens e arquivo analisado
```

Vantagem: voce nao precisa remodelar o sistema. So adiciona um modo de inferencia remota e fallback local.

---

## 2. O que voce vai preparar

1. Servidor Ubuntu com NVIDIA driver + CUDA funcionando.
2. API de inferencia dedicada no Ubuntu.
3. SSL no endpoint remoto (dominio + certificado).
4. Credenciais e secrets salvos apenas no servidor (nunca no chat).
5. API local apontando para a URL remota por variaveis de ambiente.

---

## 3. Checklist rapido

- [ ] Ubuntu com acesso de rede a partir do gateway local
- [ ] GPU visivel em `nvidia-smi`
- [ ] Python/venv configurado no Ubuntu
- [ ] API remota de inferencia rodando
- [ ] Nginx (ou Caddy) com TLS ativo
- [ ] Firewall liberando apenas portas necessarias
- [ ] Chave de API interna entre gateway e inferencia
- [ ] Timeout/retry e fallback local no gateway
- [ ] Logs de latencia (upload/inferencia/retorno)

---

## 4. Fluxo de seguranca sem expor credenciais

Use estes principios:

1. Credenciais em `.env` no servidor Ubuntu e no gateway local.
2. Nunca commitar secrets (`.gitignore`).
3. Entre APIs, usar header interno `X-Internal-Api-Key`.
4. SSL obrigatorio no trafego entre gateway e inferencia.
5. Opcional forte: VPN privada (WireGuard ou Tailscale) + SSL.

Exemplo de variaveis (placeholders):

```env
# Gateway local (Windows)
USE_REMOTE_INFERENCE=true
REMOTE_INFERENCE_URL=https://SEU_DOMINIO_OU_IP/inference/predict
REMOTE_INFERENCE_API_KEY=COLOQUE_SUA_CHAVE_AQUI
REMOTE_TIMEOUT_SECONDS=120
REMOTE_VERIFY_SSL=true

# Ubuntu (API remota)
INTERNAL_API_KEY=COLOQUE_SUA_CHAVE_AQUI
CUDA_VISIBLE_DEVICES=0,1,2
```

---

## 5. SSL no Ubuntu (sem compartilhar credenciais aqui)

Opcao A (publico): Nginx + Certbot (Let's Encrypt)

1. Aponte DNS do dominio para IP publico do Ubuntu.
2. Instale Nginx e Certbot.
3. Configure virtual host com proxy para Uvicorn/Gunicorn.
4. Emita certificado com Certbot.
5. Habilite renovacao automatica.

Comandos base (ajuste no seu ambiente):

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
sudo ufw allow 80
sudo ufw allow 443
```

Depois de configurar o server block:

```bash
sudo certbot --nginx -d SEU_DOMINIO
sudo systemctl enable certbot.timer
```

Opcao B (rede privada): WireGuard/Tailscale + certificado interno

- Recomendado quando nao quiser expor servico na internet.
- Gateway local conecta na VPN e acessa endpoint privado do Ubuntu.

---

## 6. Contrato minimo da API remota

Endpoint sugerido no Ubuntu:

- `POST /inference/predict`
- Content-Type: `multipart/form-data`
- Campos:
  - `file`: imagem/video
  - `model`: nome do modelo
  - `request_id`: id da requisicao do gateway (opcional)

Header interno obrigatorio:

- `X-Internal-Api-Key: <INTERNAL_API_KEY>`

Resposta JSON esperada:

```json
{
  "success": true,
  "message": "Analise concluida",
  "class_counts": {"chair": 3},
  "num_frames_processed": 120,
  "detected_chairs": 3,
  "frames_with_detections": 45,
  "analyzed_file": "/tmp/output.mp4",
  "analyzed_output": {
    "path": "/tmp/output.mp4",
    "filename": "output.mp4",
    "download_url": "/inference/download/output.mp4"
  },
  "boxes": [
    {
      "frame_index": 0,
      "class_id": 2,
      "class_name": "chair",
      "confidence": 0.91,
      "x1": 100,
      "y1": 120,
      "x2": 220,
      "y2": 340,
      "track_id": 7
    }
  ]
}
```

---

## 7. Alteracoes minimas no seu gateway local

No seu backend atual, adicione modo hibrido:

1. Se `USE_REMOTE_INFERENCE=true`, enviar arquivo para `REMOTE_INFERENCE_URL`.
2. Se falhar por timeout/rede, usar inferencia local como fallback.
3. Manter autenticacao Firebase, logs e regras no gateway.

Configuracoes sugeridas no arquivo de settings:

```env
USE_REMOTE_INFERENCE=true
REMOTE_INFERENCE_URL=https://SEU_DOMINIO/inference/predict
REMOTE_INFERENCE_API_KEY=COLOQUE_SUA_CHAVE_AQUI
REMOTE_TIMEOUT_SECONDS=120
REMOTE_VERIFY_SSL=true
```

Boas praticas:

- Definir timeout de conexao e leitura.
- Retry curto para erros transientes.
- Nao logar API key.
- Registrar tempos: upload, inferencia remota, resposta.

---

## 8. Operacao com 3x GTX 1080 Ti

Recomendacoes objetivas:

1. Use um worker por GPU (ou fila de jobs com atribuicao por dispositivo).
2. Defina `CUDA_VISIBLE_DEVICES=0,1,2`.
3. Monitore uso de GPU com `nvidia-smi dmon`.
4. Para videos grandes, considere pipeline por URL/arquivo compartilhado para reduzir upload repetido.

---

## 9. Testes de validacao

Teste 1: conectividade e SSL

```bash
curl -v https://SEU_DOMINIO/inference/health
```

Teste 2: autenticacao interna

- Chamar endpoint sem `X-Internal-Api-Key` deve retornar 401/403.

Teste 3: predicao remota

```bash
curl -X POST "https://SEU_DOMINIO/inference/predict" \
  -H "X-Internal-Api-Key: SUA_CHAVE" \
  -F "file=@/caminho/imagem.jpg" \
  -F "model=chair"
```

Teste 4: fallback

- Derrube temporariamente a API remota e valide que o gateway processa localmente.

---

## 10. Plano de execucao sugerido (ordem)

1. Subir API remota no Ubuntu (sem SSL, rede interna).
2. Validar inferencia com cURL.
3. Configurar Nginx + SSL.
4. Ativar validacao de chave interna.
5. Ligar gateway local ao endpoint remoto via .env.
6. Habilitar fallback local.
7. Rodar testes de carga pequenos e monitorar latencia.

---

## 11. Riscos e mitigacoes

- Risco: latencia alta para videos grandes.
  Mitigacao: compressao, upload por URL, fila assincrona.

- Risco: indisponibilidade do remoto.
  Mitigacao: fallback local + retry + circuit breaker.

- Risco: vazamento de credenciais.
  Mitigacao: secrets em .env, permissao de arquivo, rotacao de chaves.

- Risco: gargalo em unica instancia.
  Mitigacao: balanceamento por GPU/worker e monitoramento continuo.

---

## 12. Resultado esperado

Com essa estrategia, seu Windows continua como ponto de conexao do programa e a predicao pesada roda no Ubuntu com GPU NVIDIA, retornando os mesmos dados de analise com menor tempo de processamento, sem reescrever todo o sistema.
