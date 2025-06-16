/**
 * Controlador para lidar com as operações relacionadas a promoções e Server-Sent Events (SSE).
 */
const axios = require('axios'); // Já importado, mas útil para referência futura

// Carrega as variáveis de ambiente para a URL do Book Service Python
const PYTHON_BOOK_SVC_URL = `http://${process.env.PYTHON_BOOK_SVC_WEB_SERVER_HOST || 'localhost'}:${process.env.PYTHON_BOOK_SVC_WEB_SERVER_PORT || 5001}`;

// Mapa para armazenar as conexões SSE ativas do Node.js para o FRONTEND.
// Usado para encerrar streams quando o usuário desinscreve ou desconecta.
const activeFrontendSSEConnections = new Map();

/**
 * Manipula a requisição POST para registrar interesse em promoções.
 * Agora apenas confirma a intenção de subscrição para o frontend.
 * A subscrição real para o stream de promoções ocorre ao estabelecer a conexão SSE.
 *
 * @param {object} req - Objeto de requisição do Express.
 * @param {object} res - Objeto de resposta do Express.
 */
exports.subscribePromotionInterest = (req, res) => {
    const { email } = req.body;

    if (!email) {
        console.error('Error 400: Email is required for subscription.');
        return res.status(400).json({ error: 'Email is required.' });
    }

    // A subscrição para o stream será efetivada quando o cliente abrir a conexão SSE
    console.log(`Received subscription intent for email: ${email}. Client should now open SSE connection.`);
    res.status(200).json({ message: 'Subscription request received. Please connect to the promotion stream.' });
};

/**
 * Manipula a requisição POST para cancelar interesse em promoções.
 * Agora apenas confirma a intenção de desubscrição para o frontend e encerra qualquer conexão SSE ativa.
 *
 * @param {object} req - Objeto de requisição do Express.
 * @param {object} res - Objeto de resposta do Express.
 */
exports.unsubscribePromotionInterest = (req, res) => {
    const { email } = req.body;

    if (!email) {
        console.error('Error 400: Email is required for unsubscription.');
        return res.status(400).json({ error: 'Email is required.' });
    }

    // Se houver uma conexão SSE ativa do Node.js para o frontend para este e-mail, encerra-a.
    // Isso efetivamente "desinscreve" o cliente do stream.
    if (activeFrontendSSEConnections.has(email)) {
        const clientRes = activeFrontendSSEConnections.get(email);
        clientRes.end(); // Encerra a conexão SSE do Node.js para o frontend
        activeFrontendSSEConnections.delete(email);
        console.log(`SSE connection from Node.js to frontend for ${email} terminated due to unsubscription request.`);
        res.status(200).json({ message: 'Successfully unsubscribed from promotions.' });
    } else {
        // Se não houver conexão ativa, o cliente já está "desinscrito" do stream.
        console.log(`Unsubscription request for ${email}. No active SSE connection found.`);
        res.status(200).json({ message: 'Email not found in active promotion streams (already unsubscribed).' });
    }
};

/**
 * Manipula a conexão SSE para streaming de promoções.
 * Atua como um proxy, retransmitindo a stream SSE do backend Python para o frontend.
 * A "subscrição" é implícita pela manutenção desta conexão.
 *
 * @param {object} req - Objeto de requisição do Express.
 * @param {object} res - Objeto de resposta do Express.
 */
exports.streamPromotions = async (req, res) => {
    const clientEmail = req.query.email; // Pega o e-mail do frontend (será o client_id para o Python)

    if (!clientEmail) {
        console.error('Error 400: Email parameter is required for SSE connection.');
        return res.status(400).send('Email parameter is required.');
    }

    // Se já houver uma conexão SSE ativa para este e-mail, encerra a antiga antes de abrir uma nova.
    if (activeFrontendSSEConnections.has(clientEmail)) {
        console.log(`Existing SSE connection for ${clientEmail} found. Closing old connection.`);
        activeFrontendSSEConnections.get(clientEmail).end();
        activeFrontendSSEConnections.delete(clientEmail);
    }

    // Configura os cabeçalhos para SSE para a conexão Node.js -> Frontend
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    });

    // Armazena a nova conexão do Node.js para o frontend
    activeFrontendSSEConnections.set(clientEmail, res);

    console.log(`SSE connection established from Node.js to frontend for ${clientEmail}.`);
    // NOTE: Sending an initial 'connection established' message is fine,
    // but ensure it's also properly formatted for SSE.
    res.write('data: {"message": "SSE connection established."}\n\n');

    try {
        // Conecta-se ao endpoint SSE do backend Python, passando o email como client_id
        const pythonStreamResponse = await axios.get(`${PYTHON_BOOK_SVC_URL}/book/promotions-stream`, {
            params: { client_id: clientEmail }, // Envia o email como client_id
            responseType: 'stream', // Importante para Axios lidar com streams
            timeout: 0 // Sem timeout para a stream, ela deve permanecer aberta
        });

        const pythonStream = pythonStreamResponse.data;

        // Repassa os dados da stream do Python diretamente para o frontend (Node.js -> Frontend)
        pythonStream.on('data', (chunk) => {
            // Cada 'chunk' pode conter um ou mais eventos SSE.
            // O Python está enviando o JSON puro, então precisamos formatá-lo para SSE.
            const dataString = chunk.toString().trim();
            // Basic check to ensure it's not empty or just whitespace
            if (dataString) {
                // Prepend 'data: ' and append '\n\n' for proper SSE framing
                const formattedEvent = `data: ${dataString}\n\n`;
                console.log(`Forwarding formatted SSE event to frontend for ${clientEmail}:`, formattedEvent); // Log do evento formatado
                res.write(formattedEvent);
            }
        });

        pythonStream.on('end', () => {
            console.log(`Python promotion stream ended for ${clientEmail}.`);
            res.end(); // Encerra a conexão Node.js -> Frontend quando a do Python termina
            activeFrontendSSEConnections.delete(clientEmail);
        });

        pythonStream.on('error', (error) => {
            console.error(`Error in Python promotion stream for ${clientEmail}:`, error);
            // Check if headers have already been sent to avoid "ERR_STREAM_WRITE_AFTER_END"
            if (!res.headersSent) {
                res.status(500).end('Error receiving promotions from Python backend.');
            } else {
                res.end(); // Just end the response if headers already sent
            }
            activeFrontendSSEConnections.delete(clientEmail);
        });

        // Quando o cliente do frontend desconectar (browser fecha, recarrega, etc.)
        req.on('close', () => {
            console.log(`Frontend client disconnected for ${clientEmail}. Ending Python stream.`);
            // IMPORTANTE: Se o cliente frontend desconectar, devemos destruir a stream para o Python
            // para que o Python possa limpar sua fila e liberar recursos.
            pythonStream.destroy();
            activeFrontendSSEConnections.delete(clientEmail);
        });

    } catch (error) {
        console.error(`Error connecting to Python promotions stream for ${clientEmail}:`, error.message);
        if (error.response) {
            console.error('Python Backend Stream Error Data:', error.response.data);
            console.error('Python Backend Stream Status:', error.response.status);
            res.status(error.response.status).end(error.response.data.message || 'Error connecting to Python promotion stream.');
        } else {
            res.status(500).end('Internal server error or Python stream unavailable.');
        }
        activeFrontendSSEConnections.delete(clientEmail);
    }
};
