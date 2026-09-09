# 🚀 MSGWHATS - Sistema de Envio WhatsApp & Recadastro NEPOS ➔ WPS

Solução completa para gestão de mensalistas de estacionamento, automação de disparos de mensagens no WhatsApp e portal de atualização de veículos para a migração do sistema **NEPOS (cartão)** para o **WPS (Liberação por Placa / LPR)**.

---

## 🛠️ Tecnologias Utilizadas

- **Frontend & Admin**: HTML5 / CSS3 (Glassmorphism & Dark Mode) / JavaScript ES6+
- **Backend API**: Python (Flask) / Node.js
- **Banco de Dados Cloud**: **Supabase** (PostgreSQL) + Fallback SQLite local
- **Hospedagem Cloud**: **Vercel** (Serverless Deployment)
- **Exportação WPS**: Geração automática de relatórios em Excel (`.xlsx`)

---

## 🗄️ Configuração do Banco de Dados no Supabase

1. Acesse o [Supabase Dashboard](https://supabase.com) e crie um novo projeto gratuito.
2. Vá até o menu **SQL Editor** no Supabase.
3. Abra o arquivo [`supabase/schema.sql`](./supabase/schema.sql), copie todo o conteúdo e cole no Editor SQL do Supabase.
4. Clique em **Run** para criar todas as tabelas e políticas de segurança.
5. Em **Project Settings -> API**, copie:
   - `Project URL`
   - `anon public key`

---

## ⚡ Como Fazer o Deploy no Vercel

1. Acesse a [Vercel](https://vercel.com) e faça login com a sua conta GitHub **AlanGalvao83**.
2. Clique em **Add New... ➔ Project**.
3. Selecione o repositório `AlanGalvao83/MSGWHATS`.
4. Em **Environment Variables**, adicione as seguintes chaves:
   - `SUPABASE_URL` = `https://seu-projeto.supabase.co`
   - `SUPABASE_KEY` = `sua-chave-anon-publica`
5. Clique em **Deploy**! Em instantes a sua aplicação estará rodando online em `https://msgwhats.vercel.app`.

---

## 📦 Repositório GitHub

- **URL do Repositório**: `https://github.com/AlanGalvao83/MSGWHATS`

```bash
# Para enviar alterações locais para o GitHub:
git add .
git commit -m "Migracao Vercel e Supabase concluida"
git push -u origin main
```
