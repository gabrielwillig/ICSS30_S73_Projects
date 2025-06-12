/**
 * Controlador para lidar com as operações relacionadas a promoções e Server-Sent Events (SSE).
 */

// Conjunto para armazenar os e-mails dos usuários inscritos em promoções (simula um banco de dados).
const subscribedEmails = new Set();
// Mapa para armazenar as conexões SSE ativas, mapeando e-mail para o objeto de resposta (res).
const activeSSEConnections = new Map();

// Dados simulados de promoções.
const mockPromotions = [
    {
        title: "Caribbean Dream Cruise",
        discount: 20,
        expires_in: 48, // hours
        description: "Explore the beautiful islands of the Caribbean with an amazing discount! Don't miss this opportunity to relax and enjoy the sun, sea, and sand.",
        original_price: 1800.00,
        discounted_price: 1440.00,
        departure_date: "2025-08-15"
    },
    {
        title: "Mediterranean Discovery",
        discount: 15,
        expires_in: 72,
        description: "Uncover the history and charm of the Mediterranean Sea. Visit ancient cities and indulge in exquisite cuisine.",
        original_price: 2500.00,
        discounted_price: 2125.00,
        departure_date: "2025-09-10"
    },
    {
        title: "Alaskan Wilderness Expedition",
        discount: 25,
        expires_in: 24,
        description: "Embark on an unforgettable journey through the Alaskan wilderness. Witness breathtaking glaciers and abundant wildlife.",
        original_price: 3500.00,
        discounted_price: 2625.00,
        departure_date: "2025-07-01"
    },
    {
        title: "Norwegian Fjords Adventure",
        discount: 10,
        expires_in: 96,
        description: "Experience the stunning landscapes of the Norwegian Fjords. A serene and majestic voyage awaits you.",
        original_price: 2000.00,
        discounted_price: 1800.00,
        departure_date: "2025-06-20"
    }
];

/**
 * Envia uma promoção específica para um cliente via SSE.
 * @param {string} email - O e-mail do cliente para quem enviar a promoção.
 * @param {Object} promotion - O objeto de promoção a ser enviado.
 */
function sendPromotionToClient(email, promotion) {
    const res = activeSSEConnections.get(email);
    if (res && subscribedEmails.has(email)) {
        res.write(`data: ${JSON.stringify(promotion)}\n\n`);
        console.log(`Sent promotion to ${email}: ${promotion.title}`);
    } else {
        // Se a conexão não existir ou o e-mail não estiver mais inscrito, remove a conexão.
        if (res) {
            console.log(`Connection for ${email} is no longer subscribed or connection lost. Ending SSE stream.`);
            res.end(); // Encerra a conexão se o usuário não está mais inscrito
            activeSSEConnections.delete(email);
        }
    }
}

// Configura um intervalo para enviar a mesma promoção periodicamente a cada 5 segundos.
// Em um ambiente de produção, este intervalo e a lógica de envio seriam mais sofisticados.
setInterval(() => {
    // Verifica se há promoções disponíveis e clientes inscritos para enviar
    if (mockPromotions.length === 0 || subscribedEmails.size === 0) {
        return; // Não há promoções ou inscritos para enviar
    }

    // Seleciona UMA promoção aleatória para ser enviada a todos os clientes neste ciclo.
    const randomIndex = Math.floor(Math.random() * mockPromotions.length);
    const promotionToSend = mockPromotions[randomIndex];

    // Itera sobre todas as conexões SSE ativas e envia A MESMA promoção selecionada
    activeSSEConnections.forEach((res, email) => {
        sendPromotionToClient(email, promotionToSend);
    });
}, 30000); // Envia a promoção a cada 5 segundos

/**
 * Manipula a requisição POST para registrar interesse em promoções.
 * @param {object} req - Objeto de requisição do Express.
 * @param {object} res - Objeto de resposta do Express.
 */
exports.subscribePromotionInterest = (req, res) => {
    const { email } = req.body;

    if (!email) {
        console.error('Error 400: Email is required for subscription.');
        return res.status(400).json({ error: 'Email is required.' });
    }

    // Adiciona o e-mail ao conjunto de inscritos.
    subscribedEmails.add(email);
    console.log(`Email ${email} subscribed to promotions. Current subscribers:`, Array.from(subscribedEmails));

    res.status(200).json({ message: 'Successfully subscribed to promotions.' });
};

/**
 * Manipula a requisição POST para cancelar interesse em promoções.
 * @param {object} req - Objeto de requisição do Express.
 * @param {object} res - Objeto de resposta do Express.
 */
exports.unsubscribePromotionInterest = (req, res) => {
    const { email } = req.body;

    if (!email) {
        console.error('Error 400: Email is required for unsubscription.');
        return res.status(400).json({ error: 'Email is required.' });
    }

    // Remove o e-mail do conjunto de inscritos.
    const wasDeleted = subscribedEmails.delete(email);
    console.log(`Email ${email} unsubscribed from promotions. Current subscribers:`, Array.from(subscribedEmails));

    // Se houver uma conexão SSE ativa para este e-mail, encerra-a.
    if (activeSSEConnections.has(email)) {
        const clientRes = activeSSEConnections.get(email);
        clientRes.end(); // Encerra a conexão SSE
        activeSSEConnections.delete(email);
        console.log(`SSE connection for ${email} terminated due to unsubscription.`);
    }

    if (wasDeleted) {
        res.status(200).json({ message: 'Successfully unsubscribed from promotions.' });
    } else {
        res.status(404).json({ error: 'Email not found in subscriptions.' });
    }
};

/**
 * Manipula a conexão SSE para streaming de promoções.
 * @param {object} req - Objeto de requisição do Express.
 * @param {object} res - Objeto de resposta do Express.
 */
exports.streamPromotions = (req, res) => {
    const { email } = req.query; // Pega o e-mail da query parameter

    if (!email) {
        console.error('Error 400: Email parameter is required for SSE connection.');
        return res.status(400).send('Email parameter is required.');
    }

    // Configura os cabeçalhos para SSE
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    });

    // Envia um "ping" inicial para garantir que a conexão está ativa
    res.write('data: {"message": "SSE connection established."}\n\n');
    console.log(`SSE connection established for ${email}.`);

    // Adiciona a conexão ao mapa de conexões ativas
    activeSSEConnections.set(email, res);

    // Envia a primeira promoção imediatamente após a conexão, se o e-mail estiver inscrito
    if (subscribedEmails.has(email)) {
        // Envia a mesma promoção aleatória que o setInterval usaria para começar a stream
        if (mockPromotions.length > 0) {
            const randomIndex = Math.floor(Math.random() * mockPromotions.length);
            sendPromotionToClient(email, mockPromotions[randomIndex]);
        }
    }

    // Remove a conexão quando o cliente desconecta
    req.on('close', () => {
        activeSSEConnections.delete(email);
        console.log(`SSE connection closed for ${email}.`);
    });
};
