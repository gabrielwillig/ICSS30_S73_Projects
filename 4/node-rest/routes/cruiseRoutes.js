// Importa o módulo express para criar e gerenciar rotas
const express = require('express');

// Importa o controlador de cruzeiros que conterá a lógica de negócios
const cruiseController = require('../controllers/cruiseController');

// Cria uma nova instância de um roteador Express
const router = express.Router();

/**
 * @swagger
 * /api/cruises:
 * get:
 * summary: Searches for cruises based on provided parameters.
 * description: Returns a list of available cruises filtered by departure harbor, arrival harbor, and departure date.
 * parameters:
 * - in: query
 * name: departure_harbor
 * schema:
 * type: string
 * required: true
 * description: The desired departure harbor for the cruise.
 * - in: query
 * name: arrival_harbor
 * schema:
 * type: string
 * required: true
 * description: The desired arrival harbor for the cruise.
 * - in: query
 * name: departure_date
 * schema:
 * type: string
 * format: date
 * required: true
 * description: The desired departure date for the cruise (YYYY-MM-DD format).
 * responses:
 * 200:
 * description: A list of cruises.
 * content:
 * application/json:
 * schema:
 * type: array
 * items:
 * type: object
 * properties:
 * id:
 * type: string
 * description: Unique itinerary ID.
 * ship:
 * type: string
 * description: Name of the ship.
 * departure_harbor:
 * type: string
 * description: Departure harbor.
 * visiting_harbors:
 * type: array
 * items:
 * type: string
 * description: List of visiting harbors.
 * number_of_days:
 * type: integer
 * description: Duration of the cruise in days.
 * price:
 * type: number
 * format: float
 * description: Price of the cruise.
 * available_cabins:
 * type: integer
 * description: Number of available cabins.
 * available_passengers:
 * type: integer
 * description: Number of available passenger spots.
 * 400:
 * description: Incomplete search parameters.
 * content:
 * application/json:
 * schema:
 * type: object
 * properties:
 * error:
 * type: string
 * 500:
 * description: Internal server error.
 * content:
 * application/json:
 * schema:
 * type: object
 * properties:
 * error:
 * type: string
 */
// Define the GET route for '/cruises' and associate it with the searchCruises method of the controller.
router.get('/cruises', cruiseController.searchCruises);

/**
 * @swagger
 * /api/book-cruise:
 * post:
 * summary: Books a cruise itinerary.
 * description: Creates a new reservation for a cruise itinerary with the specified number of passengers and cabins.
 * requestBody:
 * required: true
 * content:
 * application/json:
 * schema:
 * type: object
 * required:
 * - itinerary_id
 * - num_passengers
 * - num_cabins
 * properties:
 * itinerary_id:
 * type: string
 * description: The unique ID of the itinerary to book.
 * num_passengers:
 * type: integer
 * description: The number of passengers for the reservation.
 * num_cabins:
 * type: integer
 * description: The number of cabins for the reservation.
 * responses:
 * 200:
 * description: Reservation successfully created.
 * content:
 * application/json:
 * schema:
 * type: object
 * properties:
 * message:
 * type: string
 * reservation_code:
 * type: string
 * payment_link:
 * type: string
 * 400:
 * description: Missing or invalid booking parameters.
 * content:
 * application/json:
 * schema:
 * type: object
 * properties:
 * error:
 * type: string
 * 500:
 * description: Internal server error.
 * content:
 * application/json:
 * schema:
 * type: object
 * properties:
 * error:
 * type: string
 */
// Define the POST route for '/book-cruise' and associate it with the bookCruise method of the controller.
router.post('/book-cruise', cruiseController.bookCruise);

/**
 * @swagger
 * /api/cancel-reservation:
 * post:
 * summary: Cancels an existing cruise reservation.
 * description: Cancels a reservation based on its unique reservation code.
 * requestBody:
 * required: true
 * content:
 * application/json:
 * schema:
 * type: object
 * required:
 * - reservation_code
 * properties:
 * reservation_code:
 * type: string
 * description: The unique reservation code to cancel.
 * responses:
 * 200:
 * description: Reservation successfully cancelled or already cancelled.
 * content:
 * application/json:
 * schema:
 * type: object
 * properties:
 * message:
 * type: string
 * 400:
 * description: Missing reservation code.
 * content:
 * application/json:
 * schema:
 * type: object
 * properties:
 * error:
 * type: string
 * 404:
 * description: Reservation not found.
 * content:
 * application/json:
 * schema:
 * type: object
 * properties:
 * error:
 * type: string
 * 500:
 * description: Internal server error.
 * content:
 * application/json:
 * schema:
 * type: object
 * properties:
 * error:
 * type: string
 */
// Define the POST route for '/cancel-reservation' and associate it with the cancelReservation method of the controller.
router.post('/cancel-reservation', cruiseController.cancelReservation);


// Export the router to be used in app.js.
module.exports = router;
