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
        const augmentedItineraries = itinerariesFromPython.map(itinerary => ({
            ...itinerary,
            // Adiciona disponibilidade mockada, já que não vem do backend Python Itinerary Service
            // Garante que haja ao menos 1 para evitar divisão por zero ou limites de 0 no front.
            available_cabins: Math.max(1, Math.floor(Math.random() * 10) + 1), // Exemplo: 1 a 10 cabines
            available_passengers: Math.max(1, Math.floor(Math.random() * 20) + 1) // Exemplo: 1 a 20 passageiros
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
 * Now communicates with the Python Book Service at /create_reservation.
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

        // Payload que será enviado para o backend Python (book_svc /create_reservation)
        // Mapeando os nomes dos campos conforme o ReservationDTO do Python
        const payloadToPython = {
            client_id: 0, // Mocked client_id as discussed for academic project
            passengers: num_passengers,
            trip_id: itinerary_id,
            price: total_price // O backend Python espera 'price' aqui para o total_price do DTO
        };

        console.log(`Forwarding booking request to Python Book Service at ${PYTHON_BOOK_SVC_URL}/create_reservation with data:`, payloadToPython);

        // Faz a requisição POST para o backend Python (MS Reserva)
        const response = await axios.post(`${PYTHON_BOOK_SVC_URL}/create_reservation`, payloadToPython, {
            timeout: 7000 // Timeout para a requisição ao backend Python
        });

        // O backend Python (MS Reserva) retorna um JSON que contém o ID da reserva
        // e o payment_link gerado pelo MS Pagamento.
        const pythonBookingResult = response.data; // Assumimos que o retorno é um objeto JSON.

        // Verifica se a resposta do Python contém os campos esperados
        if (!pythonBookingResult.id || !pythonBookingResult.payment_link) {
            console.error('Python Book Service returned unexpected data:', pythonBookingResult);
            return res.status(500).json({ error: 'Failed to create reservation: Unexpected response from booking service.' });
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
            message: 'Reservation successfully created. Proceed to payment.',
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
                error: error.response.data.error || 'Error from Python backend while booking cruise.'
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
 * @param {object} req - Express request object.
 * @param {object} res - Express response object.
 */
exports.cancelReservation = async (req, res) => {
    try {
        const { reservation_code } = req.body;

        if (!reservation_code) {
            console.error('Error 400: Reservation code is required for cancellation.');
            return res.status(400).json({ error: 'Reservation code is required.' });
        }

        const reservation = mockReservations.get(reservation_code);

        if (!reservation) {
            console.error(`Error 404: Reservation with code ${reservation_code} not found.`);
            return res.status(404).json({ error: 'Reservation not found.' });
        }

        // Simulate cancellation logic
        if (reservation.status === 'cancelled') {
            return res.status(200).json({ message: 'Reservation already cancelled.' });
        }

        reservation.status = 'cancelled';
        reservation.cancellation_timestamp = new Date().toISOString();
        mockReservations.delete(reservation_code); // Optionally remove or keep with cancelled status

        console.log(`Reservation ${reservation_code} cancelled.`);

        // In a real scenario, you would send an event to a RabbitMQ queue (e.g., 'reservation-cancelled')
        // for the Itinerary Service to consume and update its availability.

        res.status(200).json({ message: `Reservation ${reservation_code} successfully cancelled.` });

    } catch (error) {
        console.error(`Error in cancelReservation: ${error.message}`);
        res.status(500).json({ error: 'Internal server error while cancelling the reservation.' });
    }
};
