from threading import Thread
import time
import requests

import inject
from flask import Flask, request, jsonify

from book_cruises.commons.utils import config, logger
from book_cruises.commons.messaging import Consumer, Producer
from book_cruises.commons.domains import (
    Reservation,
    ReservationDTO,
    Payment,
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

        self.__reservation_repository = ReservationRepository()
        self.__itinerary_repository = ItineraryRepository()

        self.__cached_reservations = {}

        self.__thread_consumer = None

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
            config.PAYMENT_SVC_URL + "/payment/link",
            json=reservation.model_dump(),
            timeout=config.REQUEST_TIMEOUT,
        )

        logger.debug(
            f"Payment service response: {payment_res.status_code} - {payment_res.text}"
        )

    def get_payment_status(self, reservation_id):
        try:
            if not reservation_id in self.__cached_reservations:
                return {"status": "error", "message": "Reservation ID not found"}

            reservation = self.__cached_reservations[reservation_id]

            match reservation.payment_status:
                case "approved":
                    return {"status": "approved", "message": "Payment approved"}
                case "refused":
                    return {"status": "refused", "message": "Payment refused"}
                case "pending":
                    return {"status": "pending", "message": "Waiting for payment"}
                case _:
                    return {"status": "error", "message": "Unknown status"}
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return {"status": "error", "message": str(e)}

    def get_ticket_status(self, reservation_id):
        try:
            if not reservation_id in self.__cached_reservations:
                return {"status": "error", "message": "Reservation ID not found"}

            reservation = self.__cached_reservations[reservation_id]

            match reservation.ticket_status:
                case "generated":
                    return {"status": "generated", "message": "Ticket generated"}
                case "pending":
                    return {"status": "pending", "message": "Waiting for ticket"}
                case _:
                    return {"status": "error", "message": "Unknown status"}

        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return {"status": "error", "message": str(e)}

    def cancel_reservation(self, reservation_id: str) -> None:
        """
        Cancels a reservation by its ID.
        This method updates the reservation status to 'cancelled' and notifies the user.
        """
        if reservation_id not in self.__cached_reservations:
            logger.error(f"Reservation ID {reservation_id} not found.")
            return

        self.__reservation_repository.cancel_reservation(reservation_id)
        self.__cached_reservations[reservation_id].reservation_status = "cancelled"

        logger.info(f"Reservation {reservation_id} has been cancelled.")

    def __add_new_reservation(self, reservation: Reservation) -> None:
        self.__cached_reservations[reservation.id] = reservation
        logger.info(f"Added new reservation: {reservation.id}")

    def __update_reservation_payment_status(self, payment: Payment) -> None:
        self.__cached_reservations[payment.reservation_id].payment_status = (
            payment.status
        )
        logger.debug(
            f"Update reservation status: {payment.reservation_id} -> {payment.status}"
        )

    def __update_reservation_ticket_status(
        self, reservation_id: str, status: str
    ) -> None:
        self.__cached_reservations[reservation_id].ticket_status = status
        logger.info(f"Update reservation status: {reservation_id} -> {status}")

    def __process_ticket(self, payment_data: dict) -> None:
        self.__update_reservation_ticket_status(
            payment_data["message"]["payment_data"]["reservation_id"],
            "generated",
        )

    def __process_payment(self, payment_data: dict) -> None:
        payment: Payment = Payment(**payment_data)

        match payment.status:
            case "approved":
                self.__update_reservation_payment_status(payment)
                num_cabinets_to_update = self.__cached_reservations[
                    payment.reservation_id
                ].number_of_cabinets
                self.__itinerary_repository.update_remaining_cabinets(
                    payment.reservation_id, num_cabinets_to_update
                )
            case "refused":
                self.__update_reservation_payment_status(payment)
                self.cancel_reservation(payment.reservation_id)
            case _:
                logger.error(f"Unknown status: {payment.status}")

    def __target_consumer_thread(self) -> None:
        while True:
            try:
                self.__consumer.start_consuming()
            except Exception as e:
                logger.error(f"Error in thread_consumer: {e}")
                time.sleep(5)

    def __start_consumer_thread(self) -> None:
        self.__thread_consumer = Thread(
            target=self.__target_consumer_thread, daemon=True
        )
        self.__thread_consumer.start()

    def __config_broker(self) -> None:
        self.__consumer.exchange_declare(config.APP_EXCHANGE, "direct", durable=False)

        self.__consumer.queue_declare(config.RESERVE_CREATED_QUEUE, durable=False)
        self.__consumer.queue_declare(
            config.APPROVED_PAYMENT_TICKET_QUEUE, durable=False
        )
        self.__consumer.queue_declare(
            config.APPROVED_PAYMENT_BOOK_SVC_QUEUE, durable=False
        )
        self.__consumer.queue_declare(config.REFUSED_PAYMENT_QUEUE, durable=False)
        self.__consumer.queue_declare(config.TICKET_GENERATED_QUEUE, durable=False)

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


def create_flask_app(book_svc: BookSvc) -> Flask:
    app = Flask(__name__)

    @app.route("/book/get-itineraries", methods=["POST"])
    def get_itineraries():
        itinerary_data = request.json
        response = requests.post(
            config.ITINERARY_SVC_URL + "/itinerary/get-itineraries",
            json=itinerary_data,
            timeout=config.REQUEST_TIMEOUT,
        )

        return jsonify(response.json()), response.status_code

    @app.route("/book/create-reservation", methods=["POST"])
    def create_reservation():
        reservation_dto = ReservationDTO(
            client_id=request.json["client_id"],
            number_of_guests=request.json["num_of_guests"],
            number_of_cabinets=request.json["num_of_cabinets"],
            itinerary_id=request.json["itinerary_id"],
            total_price=request.json["total_price"],
        )
        result = book_svc.create_reservation(reservation_dto)
        return jsonify(result), 200

    @app.route("/book/reservation-status", methods=["GET"])
    def get_reservation_status():
        reservation_id = request.args.get("reservation_id")
        if not reservation_id:
            return (
                jsonify({"status": "error", "message": "Reservation ID is required"}),
                400,
            )

        payment_status = book_svc.get_payment_status(reservation_id)
        ticket_status = book_svc.get_ticket_status(reservation_id)

        return (
            jsonify({"payment_status": payment_status, "ticket_status": ticket_status}),
            200,
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
