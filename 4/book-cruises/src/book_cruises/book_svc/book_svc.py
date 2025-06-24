from typing import Dict
from threading import Thread
import time
import requests
from queue import Queue
import json

import inject
from flask import Flask, Response, request, jsonify, stream_with_context

from book_cruises.commons.utils import config, logger
from book_cruises.commons.messaging import Consumer, Producer
from book_cruises.commons.domains import (
    Reservation,
    ReservationDTO,
    Payment,
    Ticket,
)
from book_cruises.commons.domains.repositories import (
    ItineraryRepository,
    ReservationRepository,
)
from .di import configure_dependencies


class BookSvc:

    @inject.autoparams()
    def __init__(self, consumer: Consumer, producer: Producer):

        self.__consumer: Consumer = consumer
        self.__producer: Producer = producer

        self.__reservation_repository: ReservationRepository = ReservationRepository()
        self.__itinerary_repository: ItineraryRepository = ItineraryRepository()

        self.__cached_reservations: Dict[str, Reservation] = {}

        self.__clients_promotions_queue: Dict[str, Queue[str]] = {}

        self.__thread_consumer: Thread = None

    def run(self):
        logger.info("Book Service initialized")
        self.__config_broker()

        self.__consumer.register_callback(
            config.REFUSED_PAYMENT_QUEUE, self.__process_payment
        )
        self.__consumer.register_callback(
            config.APPROVED_PAYMENT_BOOK_SVC_QUEUE, self.__process_payment
        )
        self.__consumer.register_callback(
            config.TICKET_GENERATED_QUEUE, self.__process_ticket
        )
        self.__consumer.register_callback(
            config.PROMOTIONS_QUEUE, self.__process_promotion
        )

        self.__start_consumer_thread()

    def create_reservation(self, reservation_dto: ReservationDTO):
        reservation: Reservation = self.__reservation_repository.create_reservation(
            reservation_dto
        )

        # Store the reservation status
        self.__add_new_reservation(reservation)

        # Publish the reservation data to the RESERVE_CREATED_QUEUE
        self.__producer.publish(config.RESERVE_CREATED_QUEUE, reservation.model_dump())

        logger.debug(
            f"Published reservation {reservation.model_dump()} to {config.RESERVE_CREATED_QUEUE}"
        )

        # Solicita link de pagamento ao MS Pagamento
        payment_res = requests.post(
            f"http://{config.PAYMENT_SVC_WEB_SERVER_HOST}:{config.PAYMENT_SVC_WEB_SERVER_PORT}/payment/link",
            json=reservation.model_dump(),
            timeout=config.REQUEST_TIMEOUT,
        )

        logger.debug(f"Payment service response: {payment_res.json()}")

        return payment_res.json()

    def get_payment_status(self, reservation_id):
        if not reservation_id in self.__cached_reservations:
            return {"status": "error", "message": "Reservation ID not found"}

        reservation = self.__cached_reservations[reservation_id]

        match reservation.payment_status:
            case Payment.APPROVED:
                return {"status": Payment.APPROVED, "message": "Payment approved"}
            case Payment.REFUSED:
                return {"status": Payment.REFUSED, "message": "Payment refused"}
            case Payment.PENDING:
                return {"status": Payment.PENDING, "message": "Waiting for payment"}
            case _:
                return {"status": "error", "message": "Unknown status"}

    def get_ticket_status(self, reservation_id):
        if not reservation_id in self.__cached_reservations:
            return {"status": "error", "message": "Reservation ID not found"}

        reservation = self.__cached_reservations[reservation_id]

        match reservation.ticket_status:
            case Ticket.GENERATED:
                return {"status": Ticket.GENERATED, "message": "Ticket generated"}
            case Ticket.PENDING:
                return {"status": Ticket.PENDING, "message": "Waiting for ticket"}
            case _:
                return {"status": "error", "message": "Unknown status"}

    def cancel_reservation(self, reservation_id: str) -> None:
        """
        Cancels a reservation by its ID.
        This method updates the reservation status to 'cancelled' and notifies the user.
        """
        logger.error(self.__cached_reservations)
        if reservation_id not in self.__cached_reservations:
            logger.error(f"Reservation ID {reservation_id} not found.")
            return
        self.__reservation_repository.update_status(reservation_id, Reservation.CANCELLED)
        self.__cached_reservations[reservation_id].reservation_status = Reservation.CANCELLED

        logger.info(f"Reservation with id '{reservation_id}' has been '{Reservation.CANCELLED}'.")

    def create_client_promotion_queue(self, client_id: str) -> None:
        """
        Creates a queue for client promotions if it doesn't already exist.
        This allows the service to send promotions to specific clients.
        """
        if client_id not in self.__clients_promotions_queue:
            queue = Queue()
            self.__clients_promotions_queue[client_id] = queue
            logger.info(f"Created promotion queue for client '{client_id}'")
        else:
            logger.warning(f"Promotion queue for client '{client_id}' already exists")

        return queue

    def remove_client_promotion_queue(self, client_id: str) -> None:
        """
        Removes the client's promotion queue.
        This is useful when a client no longer needs to receive promotions.
        """
        if client_id in self.__clients_promotions_queue:
            del self.__clients_promotions_queue[client_id]
            logger.info(f"Removed promotion queue for client '{client_id}'")
        else:
            logger.warning(f"No promotion queue found for client '{client_id}'")

    def __add_new_reservation(self, reservation: Reservation) -> None:
        self.__cached_reservations[reservation.id] = reservation
        logger.info(f"Added new reservation: {reservation.id}")
        logger.debug(
            f"Cached reservations: {self.__cached_reservations.keys()}"
        )

    def __update_reservation_payment_status(self, payment: Payment) -> None:
        if not payment.reservation_id in self.__cached_reservations:
            logger.error(
                f"Reservation ID '{payment.reservation_id}' not found in cached reservations: {self.__cached_reservations.keys()}"
            )
            return
        self.__cached_reservations[payment.reservation_id].payment_status = (
            payment.status
        )
        logger.debug(
            f"Update payment status with reservation_id '{payment.reservation_id}' -> '{payment.status}'"
        )

    def __update_reservation_ticket_status(
        self, reservation_id: str, ticket: Ticket
    ) -> None:
        self.__cached_reservations[reservation_id].ticket_status = ticket.status
        logger.info(
            f"Update ticket status with reservation_id '{reservation_id}' -> '{ticket.status}'"
        )

    def __process_ticket(self, ticket_data: dict) -> None:
        ticket: Ticket = Ticket(**ticket_data)
        self.__update_reservation_ticket_status(ticket.payment.reservation_id, ticket)

    def __process_payment(self, payment_data: dict) -> None:
        payment: Payment = Payment(**payment_data)

        match payment.status:
            case Payment.APPROVED:
                self.__update_reservation_payment_status(payment)
                num_cabinets_to_update = self.__cached_reservations[
                    payment.reservation_id
                ].number_of_cabinets
                self.__reservation_repository.update_status(
                    payment.reservation_id, Reservation.APPROVED
                )
                self.__itinerary_repository.update_remaining_cabinets(
                    payment.itinerary_id, num_cabinets_to_update
                )
            case Payment.REFUSED:
                self.__update_reservation_payment_status(payment)
                self.cancel_reservation(payment.reservation_id)
            case _:
                logger.error(f"Unknown status: '{payment.status}'")

    def __process_promotion(self, promotion_data: dict) -> None:
        """
        Process a promotion message and send it each client that has subscribed to promotions.
        """
        logger.info(f"Promotion received: {promotion_data}")

        for client_id, queue in self.__clients_promotions_queue.items():
            if queue:
                queue.put(promotion_data)
                logger.info(f"Promotion sent to client {client_id}")

    def __target_consumer_thread(self) -> None:
        while True:
            try:
                self.__consumer.start_consuming()
            except Exception as e:
                logger.error(f"Error in thread_consumer", exc_info=True)
                time.sleep(5)

    def __start_consumer_thread(self) -> None:
        self.__thread_consumer = Thread(
            target=self.__target_consumer_thread, daemon=True
        )
        self.__thread_consumer.start()

    def __config_broker(self) -> None:
        self.__consumer.exchange_declare(
            exchange=config.APP_EXCHANGE, exchange_type="direct"
        )
        self.__consumer.exchange_declare(
            exchange=config.PROMOTIONS_EXCHANGE, exchange_type="topic"
        )

        self.__consumer.queue_declare(config.RESERVE_CREATED_QUEUE)
        self.__consumer.queue_declare(config.APPROVED_PAYMENT_TICKET_QUEUE)
        self.__consumer.queue_declare(config.APPROVED_PAYMENT_BOOK_SVC_QUEUE)
        self.__consumer.queue_declare(config.REFUSED_PAYMENT_QUEUE)
        self.__consumer.queue_declare(config.TICKET_GENERATED_QUEUE)
        self.__consumer.queue_declare(config.QUERY_RESERVATION_QUEUE)
        self.__consumer.queue_declare(config.PROMOTIONS_QUEUE)

        self.__consumer.queue_bind(
            queue_name=config.APPROVED_PAYMENT_BOOK_SVC_QUEUE,
            exchange=config.APP_EXCHANGE,
            routing_key=config.APPROVED_PAYMENT_ROUTING_KEY,
        )
        self.__consumer.queue_bind(
            queue_name=config.APPROVED_PAYMENT_TICKET_QUEUE,
            exchange=config.APP_EXCHANGE,
            routing_key=config.APPROVED_PAYMENT_ROUTING_KEY,
        )
        self.__consumer.queue_bind(
            queue_name=config.PROMOTIONS_QUEUE,
            exchange=config.PROMOTIONS_EXCHANGE,
            routing_key="#",  # Bind to all routing keys
        )


def create_flask_app(book_svc: BookSvc) -> Flask:
    app = Flask(__name__)

    @app.route("/book/get-itineraries", methods=["POST"])
    def get_itineraries():
        """
        Retrieves available itineraries from the itinerary service.

        Args:
            JSON body containing itinerary search criteria, with:
                - departure_harbor (str): The harbor of departure.
                - arrival_harbor (str): The harbor of arrival.
                - departure_date (str): The date of return in YYYY-MM-DD format.

        Returns:
            Response: A JSON list of itineraries from the itinerary service.
        """

        itinerary_data = request.json
        logger.info(f"Received itinerary request: {itinerary_data}")
        response = requests.post(
            f"http://{config.ITINERARY_SVC_WEB_SERVER_HOST}:{config.ITINERARY_SVC_WEB_SERVER_PORT}/itinerary/get-itineraries",
            json=itinerary_data,
            timeout=config.REQUEST_TIMEOUT,
        )

        return jsonify(response.json()), response.status_code

    @app.route("/book/create-reservation", methods=["POST"])
    def create_reservation():
        """
        Creates a reservation for a cruise based on the given client and itinerary data.

        Args:
            JSON body with:
                - client_id (str): ID of the client making the reservation.
                - num_of_passengers (int): Number of passengers included.
                - num_of_cabinets (int): Number of cabin rooms required.
                - itinerary_id (str): Selected itinerary identifier.
                - total_price (float): Total price of the reservation.

        Returns:
            Response: JSON object containing:
                - message (str): Message from payment service in case of success.
                - payment_link (str): An external link to the payment page.
                - reservation_id (str): Unique identifier for the created reservation.
        """
        logger.debug(f"Creating reservation with data: {request.json}")
        reservation_dto = ReservationDTO(
            client_id=request.json["client_id"],
            number_of_passengers=request.json["num_of_passengers"],
            number_of_cabinets=request.json["num_of_cabinets"],
            itinerary_id=request.json["itinerary_id"],
            total_price=request.json["total_price"],
        )
        result = book_svc.create_reservation(reservation_dto)
        return jsonify(result), 200

    @app.route("/book/reservation-status", methods=["GET"])
    def get_reservation_status():
        """
        Retrieves the payment and ticket status of a reservation.

        Args:
            reservation_id (str): ID of the reservation to check.

        Returns:
            Response: JSON object containing:
                - payment_status (str): Current payment status.
                - ticket_status (str): Current ticket status.

            If reservation_id is missing, returns HTTP 400 with an error message.
        """

        reservation_id = request.args.get("reservation_id")
        if not reservation_id:
            return (
                jsonify({"status": "error", "message": "Reservation ID is required"}),
                400,
            )
        
        def event_stream():
            while True:
                payment_status = book_svc.get_payment_status(reservation_id)
                ticket_status = book_svc.get_ticket_status(reservation_id)

                yield json.dumps({
                    "payment_status": payment_status,
                    "ticket_status": ticket_status
                })

                time.sleep(5)

        return Response(
            stream_with_context(event_stream()), mimetype="text/event-stream"
        )

    @app.route("/book/cancel-reservation", methods=["DELETE"])
    def cancel_reservation():
        """
        Cancels a reservation by its ID.

        Args:
            JSON body with:
                - reservation_id (str): The ID of the reservation to cancel.

        Returns:
            Response:
                - On success: JSON confirmation message with HTTP 200.
                - On failure (missing ID): JSON error message with HTTP 400.
        """

        reservation_id = request.json.get("reservation_id")
        if not reservation_id:
            return (
                jsonify({"status": "error", "message": "Reservation ID is required"}),
                400,
            )

        book_svc.cancel_reservation(reservation_id)
        return jsonify({"status": "success", "message": "Reservation cancelled"}), 200

    @app.route("/book/promotions-stream")
    def get_promotions():
        """
        When a promotion is received, it will be sent to the client as a Server-Sent Event (SSE).

        Args:
            client_id (str): The unique identifier for the client. This is used to create a dedicated queue for the client.

        Returns:
            A JSON body with the following keys:
                - title (str): Promotion title, e.g., "Special Offer to Bahamas!".
                - description (str): Description of the offer.
                - destination (str): The cruise destination.
                - itinerary_id (str): ID of the itinerary.
                - discount (float): Discount percentage applied.
                - expires_in (str): Human-readable time until expiration (e.g., "24 hours").
                - original_price (float): The original cruise price.
                - discounted_price (float): The price after applying the discount.
                - departure_date (str): The formatted departure date.
                - timestamp (str): ISO-formatted timestamp of promotion creation.
        """

        client_id = request.args.get("client_id")
        if not client_id:
            return (
                jsonify({"status": "error", "message": "Client ID is required"}),
                400,
            )

        queue = book_svc.create_client_promotion_queue(client_id)

        def event_stream():
            try:
                while True:
                    yield json.dumps(queue.get())
            except GeneratorExit:
                logger.info(f"Client {client_id} disconnected from promotions stream")
                book_svc.remove_client_promotion_queue(client_id)

        return Response(
            stream_with_context(event_stream()), mimetype="text/event-stream"
        )

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok"}), 200

    return app


def main() -> None:
    configure_dependencies()

    book_svc = BookSvc()
    book_svc.run()

    # Create and run the Flask app
    app = create_flask_app(book_svc)
    app.run(
        port=config.BOOK_SVC_WEB_SERVER_PORT,
        host=config.BOOK_SVC_WEB_SERVER_HOST,
        debug=config.DEBUG,
    )
