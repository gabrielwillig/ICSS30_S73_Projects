// Importa o módulo express
const express = require('express');
// Importa o controlador de promoções que conterá a lógica de negócios
const promotionController = require('../controllers/promotionController');

// Cria uma nova instância de um roteador Express
const router = express.Router();

/**
 * @swagger
 * /api/promotions/subscribe:
 * post:
 * summary: Registers interest in receiving promotions.
 * description: Subscribes a user's email to receive promotion notifications.
 * requestBody:
 * required: true
 * content:
 * application/json:
 * schema:
 * type: object
 * required:
 * - email
 * properties:
 * email:
 * type: string
 * format: email
 * description: The user's email address.
 * responses:
 * 200:
 * description: Successfully subscribed.
 * content:
 * application/json:
 * schema:
 * type: object
 * properties:
 * message:
 * type: string
 * 400:
 * description: Missing or invalid email.
 * content:
 * application/json: 
 * schema:
 * type: object
 * properties:
 * error:
 * type: string
 */
// Rota para registrar interesse em promoções (inscrição)
router.get('/subscribe', promotionController.subscribePromotionInterest);

/**
 * @swagger
 * /api/promotions/unsubscribe:
 * post:
 * summary: Cancels interest in receiving promotions.
 * description: Unsubscribes a user's email from promotion notifications.
 * requestBody:
 * required: true
 * content:
 * application/json:
 * schema:
 * type: object
 * required:
 * - email
 * properties:
 * email:
 * type: string
 * format: email
 * description: The user's email address to unsubscribe.
 * responses:
 * 200:
 * description: Successfully unsubscribed.
 * content:
 * application/json:
 * schema:
 * type: object
 * properties:
 * message:
 * type: string
 * 400:
 * description: Missing or invalid email.
 * content:
 * application/json:
 * schema:
 * type: object
 * properties:
 * error:
 * type: string
 */
// Rota para cancelar interesse em promoções (cancelamento de inscrição)
router.get('/unsubscribe', promotionController.unsubscribePromotionInterest);

/**
 * @swagger
 * /api/promotions/sse:
 * get:
 * summary: Establishes a Server-Sent Events (SSE) connection for promotions.
 * description: Clients can connect to this endpoint to receive real-time promotion updates.
 * parameters:
 * - in: query
 * name: email
 * schema:
 * type: string
 * format: email
 * required: true
 * description: The email address of the user initiating the SSE connection.
 * responses:
 * 200:
 * description: SSE connection established. Events will be streamed.
 * headers:
 * Content-Type:
 * schema:
 * type: string
 * example: text/event-stream
 * Cache-Control:
 * schema:
 * type: string
 * example: no-cache
 * Connection:
 * schema:
 * type: string
 * example: keep-alive
 * 400:
 * description: Missing email parameter.
 */
// Rota para a conexão SSE (Server-Sent Events) para promoções
router.get('/sse', promotionController.streamPromotions);

// Exporta o roteador para ser usado em app.js
module.exports = router;
