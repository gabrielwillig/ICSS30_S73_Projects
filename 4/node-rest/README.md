# node-rest

## Pré-requisitos
- WSL2 com sua distribuição Linux instalada
- Node.js (>=14) e yarn
- (Opcional) Serviço Python de reservas para SSE e rotas de promoções

## Instalação
1. Abra seu terminal WSL e vá para a pasta do projeto:
   ```bash
   cd 4/node-rest
   ```
2. Instale as dependências Node:
   ```bash
   yarn install
   ```
3. Crie um arquivo `.env` na raiz do projeto, pode-se utilizar o exemplo em `.envexample`
4. Subir o backend python
## Executando API + Front-end
1. No WSL, inicie o servidor Node:
   ```bash
   yarn start
   ou
   node app.js
   ```
2. No Windows, abra no navegador:
   ```
   http://localhost:3000/
   ```
3. Utilize a interface para:
   - Buscar cruzeiros  
   - Criar e cancelar reservas  
   - Inscrever/desinscrever e receber promoções em tempo real  