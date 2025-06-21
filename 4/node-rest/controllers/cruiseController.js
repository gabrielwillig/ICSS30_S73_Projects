/**
 * Controlador para lidar com as operações relacionadas a cruzeiros.
 */
const axios = require('axios'); // Importa o Axios para fazer requisições HTTP

// Carrega as variáveis de ambiente.
// Garanta que `require('dotenv').config()` esteja no seu `app.js`
// e que as variáveis PYTHON_BOOK_SVC_WEB_SERVER_HOST e PYTHON_BOOK_SVC_WEB_SERVER_PORT
// estejam definidas no seu arquivo .env.
const PYTHON_BOOK_SVC_URL = `http://${process.env.PYTHON_BOOK_SVC_WEB_SERVER_HOST || 'localhost'}:${process.env.PYTHON_BOOK_SVC_WEB_SERVER_PORT || 5001}`;

// Simula um armazenamento de reservas. Em um sistema real, isso seria um banco de dados.
// NOTA: mockReservations não será mais usado para cancelamento, mas ainda é usado para bookCruise
const mockReservations = new Map();

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
        // O Python já fornece 'remaining_cabinets'.
        // Adicionamos 'remaining_passengers' mockado para o frontend.
        const itinerariesFromPython = response.data;
        const augmentedItineraries = itinerariesFromPython.map(itinerary => ({
            ...itinerary,
            // Adiciona remaining_passengers mockado, já que não vem do backend Python
            remaining_passengers: itinerary.remaining_cabinets * 3 // Exemplo: 1 a 20 passageiros
            // remaining_cabinets já vem do Python, então não precisamos adicionar mock aqui.
            // A validação de remaining_cabinets > 0 será feita no front-end ou no serviço de itinerários Python
        }));

        res.status(response.status).json(augmentedItineraries);

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
            num_of_passengers: num_passengers, // Alterado de 'passengers' para 'num_of_passengers'
            num_of_cabinets: num_cabins, // Alterado de 'num_cabins' para 'num_of_cabinets'
            itinerary_id: itinerary_id,
            total_price: total_price
        };

        console.log(`Forwarding booking request to Python Book Service at ${PYTHON_BOOK_SVC_URL}/book/create-reservation with data:`, payloadToPython);

        // Faz a requisição POST para o backend Python (MS Reserva)
        const response = await axios.post(`${PYTHON_BOOK_SVC_URL}/book/create-reservation`, payloadToPython, {
            timeout: 7000 // Timeout para a requisição ao backend Python
        });

        // O backend Python (MS Reserva) retorna um JSON com message, payment_link, reservation_id
        const pythonBookingResult = response.data;

        // Verifica se a resposta do Python contém os campos esperados
        if (!pythonBookingResult.reservation_id || !pythonBookingResult.payment_link) {
            console.error('Python Book Service returned unexpected data (missing reservation_id or payment_link):', pythonBookingResult);
            return res.status(500).json({ error: 'Failed to create reservation: Unexpected response from booking service.' });
        }

        // Armazena a reserva localmente no Node.js (se necessário para cancelamento, etc.)
        mockReservations.set(pythonBookingResult.reservation_id, {
            ...pythonBookingResult,
            status: 'pending_payment', // Status inicial, antes de interagir com o pagamento
            timestamp: new Date().toISOString()
        });

        // Envia a resposta de volta para o frontend
        res.status(200).json({
            message: pythonBookingResult.message || 'Reservation successfully created. Proceed to payment.',
            reservation_id: pythonBookingResult.reservation_id, // Usar reservation_id do Python
            payment_link: pythonBookingResult.payment_link
        });

    } catch (error) {
        console.error(`Error in bookCruise when calling Python backend: ${error.message}`);
        // Loga a resposta de erro do backend Python, se disponível
        if (error.response) {
            console.error('Python Backend Response Error Data:', error.response.data);
            console.error('Python Backend Response Status:', error.response.status);
            res.status(error.response.status).json({
                error: error.response.data.message || 'Error from Python backend while booking cruise.'
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
 * Now communicates directly with the Python Book Service at /book/cancel-reservation using DELETE.
 *
 * @param {object} req - Express request object.
 * @param {object} res - Express response object.
 */
exports.cancelReservation = async (req, res) => {
    try {
        const { reservation_code } = req.body; // Frontend envia 'reservation_code' como string

        if (!reservation_code) {
            console.error('Error 400: Reservation code is required for cancellation.');
            return res.status(400).json({ error: 'Reservation code is required.' });
        }

        // Converte o reservation_code para um número inteiro, como esperado pelo backend Python
        const reservationIdInt = parseInt(reservation_code, 10);

        if (isNaN(reservationIdInt)) {
            console.error('Error 400: Invalid reservation code format. Must be an integer.');
            return res.status(400).json({ error: 'Invalid reservation code format. Must be an integer.' });
        }

        // Payload para o backend Python com o ID como inteiro
        const payloadToPython = {
            reservation_id: reservationIdInt // Mapeia 'reservation_code' para 'reservation_id' (int)
        };

        console.log(`Forwarding cancellation request to Python Book Service at ${PYTHON_BOOK_SVC_URL}/book/cancel-reservation with data:`, payloadToPython);

        // Faz a requisição DELETE para o backend Python (MS Reserva)
        const response = await axios.delete(`${PYTHON_BOOK_SVC_URL}/book/cancel-reservation`, {
            data: payloadToPython, // Para requisições DELETE com corpo, use 'data' no Axios
            timeout: 5000 // Timeout de 5 segundos
        });

        // O backend Python retorna um JSON como {"status": "success", "message": "Reservation cancelled"}
        const pythonCancellationResult = response.data;

        if (pythonCancellationResult.status === "success") {
            // Removemos a reserva do mock local se ela foi registrada lá, embora não seja mais a fonte principal
            if (mockReservations.has(reservation_code)) {
                mockReservations.delete(reservation_code);
                console.log(`Reservation ${reservation_code} removed from local mock.`);
            }
            res.status(200).json({ message: pythonCancellationResult.message });
        } else {
            // Caso o backend Python retorne um status de sucesso (200) mas com um status interno diferente de "success"
            res.status(200).json({ message: pythonCancellationResult.message || 'Cancellation processed with an unexpected status.' });
        }

    } catch (error) {
        console.error(`Error in cancelReservation when calling Python backend: ${error.message}`);
        // Loga a resposta de erro do backend Python, se disponível
        if (error.response) {
            console.error('Python Backend Response Error Data:', error.response.data);
            console.error('Python Backend Response Status:', error.response.status);
            res.status(error.response.status).json({
                error: error.response.data.message || 'Error from Python backend while cancelling reservation.'
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

/**
 * Retrieves the payment and ticket status of a reservation from the Python Book Service.
 *
 * @param {object} req - Express request object. Expects 'reservation_id' in query.
 * @param {object} res - Express response object.
 */
exports.getReservationStatus = async (req, res) => {
    try {
        const { reservation_id } = req.query; // Python expects 'reservation_id' in query params

        if (!reservation_id) {
            console.error('Error 400: Reservation ID is required for status check.');
            return res.status(400).json({ error: 'Reservation ID is required.' });
        }

        console.log(`Forwarding status check request for reservation ID: ${reservation_id} to Python Book Service.`);

        // Faz a requisição GET para o backend Python (MS Reserva)
        const response = await axios.get(`${PYTHON_BOOK_SVC_URL}/book/reservation-status`, {
            params: { reservation_id: parseInt(reservation_id, 10) }, // Passa o ID como query parameter (agora como int)
            timeout: 5000 // Timeout de 5 segundos
        });

        // O Python retorna {"payment_status": "...", "ticket_status": "..."}
        res.status(response.status).json(response.data);

    } catch (error) {
        console.error(`Error in getReservationStatus when calling Python backend: ${error.message}`);
        if (error.response) {
            console.error('Python Backend Response Error Data:', error.response.data);
            console.error('Python Backend Response Status:', error.response.status);
            res.status(error.response.status).json({
                error: error.response.data.message || 'Error from Python backend while checking reservation status.'
            });
        } else if (error.request) {
            console.error('No response received from Python backend:', error.request);
            res.status(504).json({ error: 'Gateway Timeout: No response from Python backend for status check.' });
        } else {
            console.error('Error setting up request to Python backend:', error.message);
            res.status(500).json({ error: 'Internal server error while setting up reservation status check.' });
        }
    }
};
