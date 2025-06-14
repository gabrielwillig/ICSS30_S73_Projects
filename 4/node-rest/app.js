require('dotenv').config();

const express = require('express');
const app = express();
const path = require('path');
const cruiseRoutes = require('./routes/cruiseRoutes');
// Importa as novas rotas de promoções
const promotionRoutes = require('./routes/promotionRoutes');

app.use(express.json());

// Rota para a API de cruzeiros
app.use('/api', cruiseRoutes);
// Rota para a API de promoções e SSE
app.use('/api/promotions', promotionRoutes);

// Servir arquivos estáticos da pasta 'public'
app.use(express.static(path.join(__dirname, 'public')));

// Rota fallback para o index.html, ignorando as rotas da API
app.get('*', (req, res, next) => {
  // Se a requisição for para qualquer rota da API, continue para o próximo middleware
  if (req.path.startsWith('/api')) return next();
  // Caso contrário, envie o arquivo index.html
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`API running on http://localhost:${PORT}`));