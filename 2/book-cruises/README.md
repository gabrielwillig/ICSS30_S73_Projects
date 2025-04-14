# 🧰 Projeto com RabbitMQ, PostgreSQL e Microserviços

## 📦 Instruções de Uso

### 1. Subir o Ambiente Completo

Para iniciar o RabbitMQ, PostgreSQL e o serviço de inicialização do banco de dados (`db_init`):

```bash
docker compose up -d
```

- **RabbitMQ**:
  - Acesse a interface web: [http://localhost:15672](http://localhost:15672)  
  - **Usuário:** `user`  
  - **Senha:** `password`

- **PostgreSQL**:
  - Porta: `5432`
  - **Usuário:** `user`  
  - **Senha:** `password`  
  - **Banco de Dados:** `book-cruises`

- **Serviço de Inicialização (`db_init`)**:
  - Este serviço cria as tabelas necessárias e insere dados iniciais no banco de dados, caso ainda não existam.

---

## 🛠 Ambiente de Desenvolvimento (Dev)

### Pré-requisitos

1. Instale a ferramenta [`uv`](https://github.com/astral-sh/uv):

   ```bash
   curl -Ls https://astral.sh/uv/install.sh | sh
   ```

   > Certifique-se de que o binário `uv` esteja no seu `PATH`.

2. Certifique-se de que o PostgreSQL e o RabbitMQ estejam em execução. Você pode usar o comando:

   ```bash
   docker compose up -d postgres rabbitmq
   ```

### Executar e depurar microserviços

Execute individualmente qualquer microserviço com:

```bash
uv run <nome-do-microservico>
```

Exemplo:

```bash
uv run book-cruises
```

---

## 🚀 Ambiente de Produção (Prd)

### Subir o Ambiente Completo

Atualize o arquivo `docker-compose.yml` com os microserviços desejados.  
Depois, execute o comando:

```bash
docker compose up -d
```

Todos os containers serão iniciados conforme definidos no compose.

### Verificar o Banco de Dados

Após subir o ambiente, você pode verificar o banco de dados PostgreSQL:

1. Acesse o container do PostgreSQL:

   ```bash
   docker exec -it postgres psql -U user -d book-cruises
   ```

2. Liste as tabelas:

   ```sql
   \dt
   ```

3. Consulte os dados iniciais (exemplo para a tabela `itineraries`):

   ```sql
   SELECT * FROM itineraries;
   ```

---

## 🗂 Estrutura do Projeto

- **`src/book_cruises/commons/utils/infra/db_init.py`**:
  - Script responsável por criar as tabelas e inserir dados iniciais no banco de dados.

- **`docker-compose.yaml`**:
  - Define os serviços do RabbitMQ, PostgreSQL e o inicializador do banco de dados (`db_init`).

- **`Dockerfile`**:
  - Configura o ambiente para os microserviços.

---

## 🐳 Serviços no Docker Compose

### RabbitMQ

- Porta AMQP: `5672`
- Interface Web: [http://localhost:15672](http://localhost:15672)

### PostgreSQL

- Porta: `5432`
- Banco de Dados: `book-cruises`

### Serviço de Inicialização (`db_init`)

- Executa o script `db_init.py` para criar tabelas e inserir dados iniciais.
- Este serviço é executado automaticamente ao subir o ambiente.

---

## 📋 Comandos Úteis

### Subir o Ambiente

```bash
docker compose up -d
```

### Parar o Ambiente

```bash
docker compose down
```

### Ver Logs de um Serviço

```bash
docker logs <nome-do-servico>
```

Exemplo:

```bash
docker logs db_init
```

### Acessar o Banco de Dados

```bash
docker exec -it postgres psql -U user -d book-cruises
```

---

## 🛠 Solução de Problemas

### PostgreSQL não está acessível

Certifique-se de que o serviço `postgres` está em execução:

```bash
docker ps
```

Se o serviço não estiver rodando, reinicie o ambiente:

```bash
docker compose up -d
```

### Serviço `db_init` falhou

Verifique os logs do serviço:

```bash
docker logs db_init
```

Se necessário, execute o script manualmente:

```bash
docker exec -it db_init python src/book_cruises/commons/utils/infra/db_init.py
```

---
