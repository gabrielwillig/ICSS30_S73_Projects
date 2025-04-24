import inject
import json
import threading
import time
from flask import Flask, request, jsonify
from book_cruises.commons.utils import config, logger, cryptographer
from book_cruises.commons.messaging import Consumer, Producer
from book_cruises.commons.database import Database
from book_cruises.commons.domains import ItineraryDTO
from book_cruises.commons.domains.repositories import ItineraryRepository
from .di import configure_dependencies


class BookSvc:
    @inject.autoparams()
    def __init__(self, consumer: Consumer, producer: Producer, database: Database):
        self.__PAYMENT_PUBLIC_KEY_PATH = (
            "src/book_cruises/book_svc/public_keys/payment_svc_public_key.pem"
        )
        self.__payment_public_key = cryptographer.load_public_key(self.__PAYMENT_PUBLIC_KEY_PATH)

        self.__consumer: Consumer = consumer
        self.__producer: Producer = producer
        self.__repository = ItineraryRepository(database)

        self.__reservation_statuses = {}
        self.__app = Flask(__name__)
        self.__app.add_url_rule(
            "/create_reservation", view_func=self.create_reservation, methods=["POST"]
        )

        self.__thread_consumer = threading.Thread(
            target=self.__consumer.start_consuming, daemon=True
        )
        self.__thread_web_server = threading.Thread(
            target=self.__app.run,
            kwargs={
                "port": config.BOOK_SVC_WEB_SERVER_PORT,
                "host": config.BOOK_SVC_WEB_SERVER_HOST,
            },
        )

    def __update_reservation_status(self, reservation_id: str, status: str) -> None:
        logger.info(f"Updating reservation status: {reservation_id} -> {status}")
        self.__reservation_statuses[reservation_id] = status

    def __query_itinerary(self, itinerary_data: dict) -> list:
        try:
            itinerary_dto = ItineraryDTO(**itinerary_data)

            itineraries = self.__repository.get_itineraries(itinerary_dto)
            logger.debug(f"Available itineraries: {itineraries}")

            list_itineraries_dict = []
            for itinerary in itineraries:
                itinerary_json = itinerary.json()
                list_itineraries_dict.append(json.loads(itinerary_json))

            return list_itineraries_dict

        except Exception as e:
            logger.error(f"Failed to process message: {e}")

    def __process_ticket(self, payment_data: dict) -> None:
        logger.info(f"Updating reservation status with ticket data: {payment_data}")
        self.__update_reservation_status(
            payment_data["message"]["payment_data"]["reservation_id"], "ticket_generated"
        )

    def __process_payment(self, payment_data: dict) -> None:
        signature_is_valid = cryptographer.verify_signature(
            payment_data["message"],
            payment_data["signature"],
            self.__payment_public_key,
        )
        if not signature_is_valid:
            logger.error("Invalid signature")
            raise NotImplementedError("Invalid signature")

        message = payment_data["message"]
        status = message["status"]

        match status:
            case "approved":
                logger.info(f"Processing approved payment with data: {message}")
            case "refused":
                logger.error(f"Processing refused payment with data: {message}")
                self.__update_reservation_status(
                    message["payment_data"]["reservation_id"], "refused"
                )
            case _:
                logger.error(f"Unknown status: {status}")

    def create_reservation(self):
        try:
            # Extract reservation data from the request
            reservation_data = request.json
            reservation_id = f"res-{int(time.time())}"  # Generate a unique reservation ID
            reservation_data["reservation_id"] = reservation_id

            # Publish the reservation data to the RESERVE_CREATED_QUEUE
            self.__producer.publish(config.RESERVE_CREATED_QUEUE, reservation_data)
            logger.info(f"Published reservation {reservation_id} to {config.RESERVE_CREATED_QUEUE}")

            # Wait for a response from the queues
            timeout = 30  # Timeout in seconds
            start_time = time.time()
            while time.time() - start_time < timeout:
                if reservation_id in self.__reservation_statuses:
                    status = self.__reservation_statuses[reservation_id]
                    if status == "approved":
                        return (
                            jsonify({"status": "approved", "message": "Reservation approved"}),
                            200,
                        )
                    elif status == "refused":
                        return jsonify({"status": "refused", "message": "Reservation refused"}), 400
                    elif status == "ticket_generated":
                        return (
                            jsonify({"status": "ticket_generated", "message": "Ticket generated"}),
                            200,
                        )
                time.sleep(1)

            # If no response is received within the timeout, return a timeout error
            return jsonify({"status": "timeout", "message": "No response received"}), 504

        except Exception as e:
            logger.error(f"Error creating reservation: {e}")
            return jsonify({"status": "error", "message": "An error occurred"}), 500

    def run(self):
        logger.info("Book Service initialized")
        self.__consumer.declare_queue(config.QUERY_RESERVATION_QUEUE, durable=False)
        self.__consumer.declare_queue(config.RESERVE_CREATED_QUEUE, durable=False)
        self.__consumer.declare_queue(config.APPROVED_PAYMENT_QUEUE, durable=False)
        self.__consumer.declare_queue(config.REFUSED_PAYMENT_QUEUE, durable=False)
        self.__consumer.declare_queue(config.TICKET_GENERATED_QUEUE, durable=False)

        self.__consumer.register_callback(config.QUERY_RESERVATION_QUEUE, self.__query_itinerary)
        self.__consumer.register_callback(config.REFUSED_PAYMENT_QUEUE, self.__process_payment)
        # self.__consumer.register_callback(config.APPROVED_PAYMENT_QUEUE, self.__process_payment)
        self.__consumer.register_callback(config.TICKET_GENERATED_QUEUE, self.__process_ticket)

        self.__thread_consumer.start()
        self.__thread_web_server.start()


def main() -> None:
    configure_dependencies()

    book_svc = BookSvc()
    book_svc.run()
