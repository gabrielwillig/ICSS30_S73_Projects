/**
 * Controlador para lidar com as operações relacionadas a cruzeiros.
 */
const axios = require('axios');
const PYTHON_BOOK_SVC_URL = `http://${process.env.PYTHON_BOOK_SVC_WEB_SERVER_HOST || 'localhost'}:${process.env.PYTHON_BOOK_SVC_WEB_SERVER_PORT || 5001}`;

/**
 * Função para buscar cruzeiros com base nos parâmetros fornecidos.
 * Esta função agora faz uma requisição POST para o backend Python.
 *
 * @param {object} req - O objeto de requisição do Express.
 * @param {object} res - O objeto de resposta do Express.
 * @returns {Promise<void>} - Uma promessa que resolve quando a resposta é enviada.
 */
exports.searchCruises = async (req, res) => {
    try {
        // Extrai os parâmetros da query string da requisição do frontend (Node.js)
        const { departure_harbor, arrival_harbor, departure_date } = req.query;

        // Validação de campos em inglês para manter a consistência da interface
        if (!departure_harbor || !arrival_harbor || !departure_date) {
            console.error('Error 400: Incomplete search parameters.');
            return res.status(400).json({ error: 'Incomplete search parameters. Please provide departure_harbor, arrival_harbor, and departure_date.' });
        }

        console.log(`Received request to search for cruises from frontend:`);
        console.log(`  Departure Harbor: ${departure_harbor}`);
        console.log(`  Arrival Harbor: ${arrival_harbor}`);
        console.log(`  Departure Date: ${departure_date}`);

        // Objeto de dados para enviar ao backend Python
        const itineraryData = {
            departure_harbor,
            arrival_harbor,
            departure_date
        };

        console.log(`Forwarding request to Python backend at ${PYTHON_BOOK_SVC_URL}/book/get-itineraries with data:`, itineraryData);

        // Faz a requisição POST para o seu backend Python (MS Reserva)
        const response = await axios.post(`${PYTHON_BOOK_SVC_URL}/book/get-itineraries`, itineraryData, {
            timeout: 5000 // Timeout de 5 segundos para a requisição ao backend Python
        });

        // Os dados vêm do Python com a estrutura definida (id, ship, departure_date, etc.).
        // Adicionamos 'available_cabins' e 'available_passengers' para o frontend.
        const itinerariesFromPython = response.data;
        console.log(`Received: `, itinerariesFromPython);

        // Enriquecemos cada itinerário:
        const enrichedItineraries = itinerariesFromPython.map(it => ({
            ...it,
            remaining_passengers: it.remaining_cabinets * 3
        }));

        res.status(response.status).json(enrichedItineraries);

    } catch (error) {
        console.error(`Error in searchCruises when calling Python backend: ${error.message}`);
        // Loga a resposta de erro do backend Python, se disponível
        if (error.response) {
            console.error('Python Backend Response Error Data:', error.response.data);
            console.error('Python Backend Response Status:', error.response.status);
            res.status(error.response.status).json({
                error: error.response.data.error || 'Error from Python backend while searching for cruises.'
            });
        } else if (error.request) {
            // A requisição foi feita, mas nenhuma resposta foi recebida
            console.error('No response received from Python backend:', error.request);
            res.status(504).json({ error: 'Gateway Timeout: No response from Python backend for cruise search.' });
        } else {
            // Algo aconteceu ao configurar a requisição que disparou um erro
            console.error('Error setting up request to Python backend:', error.message);
            res.status(500).json({ error: 'Internal server error while setting up cruise search.' });
        }
    }
};

/**
 * Handles the booking of a cruise.
 * Now communicates with the Python Book Service at /book/create-reservation.
 *
 * @param {object} req - Express request object.
 * @param {object} res - Express response object.
 */
exports.bookCruise = async (req, res) => {
    try {
        // Recebe os dados do frontend (itinerary_id, num_passengers, num_cabins, e agora total_price)
        const { itinerary_id, num_passengers, num_cabins, total_price } = req.body;

        if (!itinerary_id || !num_passengers || !num_cabins || isNaN(total_price) || total_price <= 0) {
            console.error('Error 400: Missing or invalid booking parameters.');
            return res.status(400).json({ error: 'Missing or invalid booking parameters. Please provide itinerary_id, num_passengers, num_cabins, and a valid total_price.' });
        }

        if (num_passengers <= 0 || num_cabins <= 0) {
            console.error('Error 400: Number of passengers and cabins must be greater than 0.');
            return res.status(400).json({ error: 'Number of passengers and cabins must be greater than 0.' });
        }

        // Payload que será enviado para o backend Python (book_svc /book/create-reservation)
        // Mapeando os nomes dos campos conforme o ReservationDTO do Python
        const payloadToPython = {
            client_id: 0, // Mocked client_id as discussed for academic project
            num_of_guests: num_passengers, // Alterado de 'passengers' para 'num_of_guests'
            num_of_cabinets: num_cabins, // Alterado de 'num_cabins' para 'num_of_cabinets'
            itinerary_id: itinerary_id,
            total_price: total_price
        };

        console.log(`Forwarding booking request to Python Book Service at ${PYTHON_BOOK_SVC_URL}/book/create-reservation with data:`, payloadToPython);

        // Faz a requisição POST para o backend Python (MS Reserva)
        const response = await axios.post(`${PYTHON_BOOK_SVC_URL}/book/create-reservation`, payloadToPython, {
            timeout: 7000 // Timeout para a requisição ao backend Python
        });

        // O backend Python (MS Reserva) retorna um JSON que contém o ID da reserva
        // e o payment_link gerado pelo MS Pagamento.
        const pythonBookingResult = response.data; // Assumimos que o retorno é um objeto JSON.
        console.log(`Received booking response from Python:`, pythonBookingResult);
        // Verifica se a resposta do Python contém os campos esperados (id e payment_link)
        // Se o Python agora só retorna { message: 'External payment service is processing...' },
        // então não teremos id nem payment_link aqui, e a lógica de polling precisará de um ID
        // gerado ou retornado de forma diferente.
        // ASSUMIR QUE O PYTHON AINDA RETORNA 'id' e 'payment_link' NO CORPO DA RESPOSTA.
        if (!pythonBookingResult.id || !pythonBookingResult.payment_link) {
            // Este bloco será ativado se o Python não retornar 'id' ou 'payment_link'.
            // Se o Python apenas retornar { message: '...' }, você precisaria de
            // um ID de reserva de alguma outra forma para fazer o polling.
            // Para este caso, vamos assumir que 'id' e 'payment_link' *ainda* vêm na resposta inicial.
            console.error('Python Book Service returned unexpected data (missing id or payment_link):', pythonBookingResult);
            // Fallback: Gerar um ID localmente se o Python não fornecer (menos ideal)
            const fallbackReservationId = `RES_FALLBACK_${Date.now()}`;
            const fallbackPaymentLink = `https://mock-payment.com/fallback-pay?id=${fallbackReservationId}`;
            console.warn(`Falling back to local reservation ID and payment link for polling: ${fallbackReservationId}`);
            res.status(200).json({
                message: pythonBookingResult.message || 'Reservation creation initiated. Checking status...',
                reservation_code: fallbackReservationId,
                payment_link: fallbackPaymentLink
            });
            return; // Termina a função aqui para evitar processar o resto com dados inconsistentes
        }

        // Armazena a reserva localmente no Node.js (se necessário para cancelamento, etc.)
        // Usamos o 'id' retornado pelo Python como o reservation_code
        mockReservations.set(pythonBookingResult.id, {
            ...pythonBookingResult,
            status: 'pending_payment', // Status inicial, antes de interagir com o pagamento
            timestamp: new Date().toISOString()
        });

        // Envia a resposta de volta para o frontend
        res.status(200).json({
            message: pythonBookingResult.message || 'Reservation successfully created. Proceed to payment.',
            reservation_code: pythonBookingResult.id, // ID da reserva do Python
            payment_link: pythonBookingResult.payment_link
        });

    } catch (error) {
        console.error(`Error in bookCruise when calling Python backend: ${error.message}`);
        // Loga a resposta de erro do backend Python, se disponível
        if (error.response) {
            console.error('Python Backend Response Error Data:', error.response.data);
            console.error('Python Backend Response Status:', error.response.status);
            res.status(error.response.status).json({
                error: error.response.data.error || error.response.data.message || 'Error from Python backend while booking cruise.'
            });
        } else if (error.request) {
            // A requisição foi feita, mas nenhuma resposta foi recebida
            console.error('No response received from Python backend:', error.request);
            res.status(504).json({ error: 'Gateway Timeout: No response from Python backend for booking.' });
        } else {
            // Algo aconteceu ao configurar a requisição que disparou um erro
            console.error('Error setting up request to Python backend:', error.message);
            res.status(500).json({ error: 'Internal server error while setting up cruise booking.' });
        }
    }
};

/**
 * Handles the cancellation of a reservation.
 * Now communicates with the Python Book Service at /book/cancel-reservation using DELETE.
 *
 * @param {object} req - Express request object.
 * @param {object} res - Express response object.
 */
exports.cancelReservation = async (req, res) => {
    try {
        const { reservation_code } = req.body; // Frontend envia 'reservation_code'

        if (!reservation_code) {
            console.error('Error 400: Reservation code is required for cancellation.');
            return res.status(400).json({ error: 'Reservation code is required.' });
        }

        // Payload para o backend Python
        const payloadToPython = {
            reservation_id: reservation_code // Mapeia 'reservation_code' para 'reservation_id'
        };

        console.log(`Forwarding cancellation request to Python Book Service at ${PYTHON_BOOK_SVC_URL}/book/cancel-reservation with data:`, payloadToPython);

        // Faz a requisição DELETE para o backend Python (MS Reserva)
        const response = await axios.delete(`${PYTHON_BOOK_SVC_URL}/book/cancel-reservation`, {
            data: payloadToPython, // Para requisições DELETE com corpo, use 'data' no Axios
            timeout: 5000 // Timeout de 5 segundos
        });

        // O backend Python retorna um JSON como {"status": "success", "message": "Reservation cancelled"}
        // Podemos usar a mensagem diretamente
        const pythonCancellationResult = response.data;

        if (pythonCancellationResult.status === "success") {
            // Se a API Python confirmar o sucesso, removemos do mock local
            if (mockReservations.has(reservation_code)) {
                mockReservations.delete(reservation_code);
                console.log(`Reservation ${reservation_code} removed from local mock.`);
            }
            res.status(200).json({ message: pythonCancellationResult.message });
        } else {
            // Caso o backend Python retorne um status de sucesso mas a mensagem não seja de sucesso.
            // (Ex: pode retornar 200 com "Reservation already cancelled")
            res.status(200).json({ message: pythonCancellationResult.message });
        }

    } catch (error) {
        console.error(`Error in cancelReservation when calling Python backend: ${error.message}`);
        // Loga a resposta de erro do backend Python, se disponível
        if (error.response) {
            console.error('Python Backend Response Error Data:', error.response.data);
            console.error('Python Backend Response Status:', error.response.status);
            res.status(error.response.status).json({
                error: error.response.data.message || 'Error from Python backend while cancelling reservation.' // Use .message para erro
            });
        } else if (error.request) {
            // A requisição foi feita, mas nenhuma resposta foi recebida
            console.error('No response received from Python backend:', error.request);
            res.status(504).json({ error: 'Gateway Timeout: No response from Python backend for cancellation.' });
        } else {
            // Algo aconteceu ao configurar a requisição que disparou um erro
            console.error('Error setting up request to Python backend:', error.message);
            res.status(500).json({ error: 'Internal server error while setting up reservation cancellation.' });
        }
    }
};
