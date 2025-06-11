/**
 * Controlador para lidar com as operações relacionadas a cruzeiros.
 */

// Simula um armazenamento de reservas. Em um sistema real, isso seria um banco de dados.
// Usaremos um Map para facilitar a busca por reservation_code.
const mockReservations = new Map();

/**
 * Função para buscar cruzeiros com base nos parâmetros fornecidos.
 * Esta função recebe os parâmetros via query string (GET request).
 *
 * @param {object} req - O objeto de requisição do Express.
 * @param {object} res - O objeto de resposta do Express.
 * @returns {Promise<void>} - Uma promessa que resolve quando a resposta é enviada.
 */
exports.searchCruises = async (req, res) => {
    try {
        // Extrai os parâmetros da query string da requisição
        const { departure_harbor, arrival_harbor, departure_date } = req.query;

        // Validação de campos em inglês para manter a consistência da interface
        if (!departure_harbor || !arrival_harbor || !departure_date) {
            console.error('Error 400: Incomplete search parameters.');
            return res.status(400).json({ error: 'Incomplete search parameters. Please provide departure_harbor, arrival_harbor, and departure_date.' });
        }

        console.log(`Received request to search for cruises:`);
        console.log(`  Departure Harbor: ${departure_harbor}`);
        console.log(`  Arrival Harbor: ${arrival_harbor}`);
        console.log(`  Departure Date: ${departure_date}`);

        // Mock data with the expected structure from the backend
        // Added available_cabins and available_passengers
        const mockCruises = [
            {
                id: 'ITN001', // Itinerary ID
                ship: 'Wonder of the Seas', // Ship name
                departure_harbor: 'Miami', // Departure harbor
                visiting_harbors: ['Nassau', 'Freeport', 'CocoCay'], // List of visiting harbors
                number_of_days: 7, // Duration in days
                price: 1500.00, // Price
                departure_date: '2025-12-25',
                available_cabins: 10, // Available cabins
                available_passengers: 20 // Available passenger spots
            },
            {
                id: 'ITN002',
                ship: 'Mediterranean Jewel',
                departure_harbor: 'Barcelona',
                visiting_harbors: ['Marseille', 'Civitavecchia', 'Naples'],
                number_of_days: 10,
                price: 2200.00,
                departure_date: '2025-10-10',
                available_cabins: 5,
                available_passengers: 10
            },
            {
                id: 'ITN003',
                ship: 'Northern Star',
                departure_harbor: 'Copenhagen',
                visiting_harbors: ['Oslo', 'Stockholm', 'Helsinki'],
                number_of_days: 12,
                price: 2800.00,
                departure_date: '2025-11-01',
                available_cabins: 0, // This itinerary will be filtered out due to 0 cabins
                available_passengers: 0 // This itinerary will be filtered out due to 0 passengers
            },
            {
                id: 'ITN004',
                ship: 'Test Vessel',
                departure_harbor: departure_harbor,
                visiting_harbors: [arrival_harbor, 'Another Port'],
                number_of_days: 5,
                price: 999.00,
                departure_date: departure_date,
                available_cabins: 2,
                available_passengers: 4
            },
            {
                id: 'ITN005',
                ship: 'Pacific Explorer',
                departure_harbor: 'Miami',
                visiting_harbors: ['Cancun', 'Key West'],
                number_of_days: 4,
                price: 800.00,
                departure_date: '2025-12-25', // Same date as ITN001 for demonstration
                available_cabins: 0, // This will also be filtered out
                available_passengers: 5
            }
        ];

        // Filter out itineraries where available_cabins or available_passengers are 0
        const filteredCruises = mockCruises.filter(cruise =>
            cruise.available_cabins > 0 && cruise.available_passengers > 0
        );

        res.status(200).json(filteredCruises);

    } catch (error) {
        // Log the error for debugging
        console.error(`Error in searchCruises: ${error.message}`);
        // Send an error response to the client
        res.status(500).json({ error: 'Internal server error while searching for cruises.' });
    }
};

/**
 * Handles the booking of a cruise.
 * @param {object} req - Express request object.
 * @param {object} res - Express response object.
 */
exports.bookCruise = async (req, res) => {
    try {
        const { itinerary_id, num_passengers, num_cabins } = req.body;

        if (!itinerary_id || !num_passengers || !num_cabins) {
            console.error('Error 400: Missing booking parameters.');
            return res.status(400).json({ error: 'Missing booking parameters. Please provide itinerary_id, num_passengers, and num_cabins.' });
        }

        // Basic validation for numbers
        if (num_passengers <= 0 || num_cabins <= 0) {
            console.error('Error 400: Number of passengers and cabins must be greater than 0.');
            return res.status(400).json({ error: 'Number of passengers and cabins must be greater than 0.' });
        }

        // Simulate interaction with "Itinerary Service" to check actual availability.
        // For now, we'll just assume it's available for the sake of the mock,
        // as the `searchCruises` already filtered out unavailable ones.
        // In a real scenario, you'd fetch the itinerary by ID and check its current availability.

        // Simulate creating a reservation and generating a payment link
        const reservationCode = `RES-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
        const paymentLink = `https://mock-payment.com/pay?code=${reservationCode}&amount=10000.00`; // Mock payment link

        const reservationDetails = {
            itinerary_id,
            num_passengers,
            num_cabins,
            reservationCode,
            paymentLink,
            status: 'pending_payment',
            timestamp: new Date().toISOString()
        };

        mockReservations.set(reservationCode, reservationDetails);
        console.log(`Reservation created: ${JSON.stringify(reservationDetails)}`);

        // In a real scenario, you would send an event to a RabbitMQ queue (e.g., 'reservation-created')
        // for the Itinerary Service to consume and update its availability.

        res.status(200).json({
            message: 'Reservation successfully created. Proceed to payment.',
            reservation_code: reservationCode,
            payment_link: paymentLink
        });

    } catch (error) {
        console.error(`Error in bookCruise: ${error.message}`);
        res.status(500).json({ error: 'Internal server error while booking the cruise.' });
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
