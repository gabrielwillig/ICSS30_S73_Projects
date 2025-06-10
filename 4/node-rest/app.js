const path = require('path')
const express = require('express')
const app = express()
const cruiseRoutes = require('./routes/cruiseRoutes')

// JSON API + SSE under /api
app.use('/api', cruiseRoutes)

// serve public/index.html, public/script.js, public/style.css...
app.use(express.static(path.join(__dirname, 'public')))

// SPA fallback (para caso de rotas client-side)
app.get('*', (req, res, next) => {
  if (req.path.startsWith('/api')) return next()
  res.sendFile(path.join(__dirname, 'public', 'index.html'))
})

const PORT = process.env.PORT || 3000
app.listen(PORT, () => console.log(`UI + API rodando em http://localhost:${PORT}`))