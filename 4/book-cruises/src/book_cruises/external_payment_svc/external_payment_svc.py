import time
import inject
import random
import requests

from typing import Dict, Union
from threading import Thread
from flask import Flask, request, jsonify

from book_cruises.commons.utils import config, logger
from book_cruises.commons.domains import Payment 

PROCESSING_DELAY = 6  # seconds


class ExternalPaymentSvc:
    @inject.autoparams()
    def __init__(self):
        self.__cached_payments: Dict[int, Payment] = {}

    def process_payment(self, payment: Payment):
        """
        Simulates processing a payment and calls a webhook indicating whether the payment was approved or refused.
        """
        logger.info("External service processing payment...")

        # Simulate a delay to mimic real-world processing time
        time.sleep(PROCESSING_DELAY)

        if random.choice([True, False]):
            payment.status = Payment.APPROVED
            logger.info("Payment approved")
        else:
            payment.status = Payment.REFUSED
            logger.warning("Payment refused")

        webhook_url = f"http://{config.PAYMENT_SVC_WEB_SERVER_HOST}:{config.PAYMENT_SVC_WEB_SERVER_PORT}/payment/notify"
        requests.post(
            webhook_url, json=payment.model_dump(), timeout=config.REQUEST_TIMEOUT
        )
        self.__remove_payment(payment.id)

    def generate_payment_link(self, payment: Payment) -> tuple[dict, int]:
        if not payment.reservation_id or not payment.client_id:
            return {"error": "Missing fields"}, 400
        
        self.__add_new_payment(payment)
        
        payment_data = {
            "reservation_id": payment.reservation_id,
            "payment_link": f"http://{config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_HOST}:{config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_PORT}/external/payment_link?payment_id={payment.id}",
            "message": "Processing payment ...",
        }
        return payment_data, 200

    def __remove_payment(self, payment_id: Union[str, int]):
        """
        Removes a payment from the cache.
        """
        payment_id_int = int(payment_id) if isinstance(payment_id, str) else payment_id
        
        if payment_id_int in self.__cached_payments:
            del self.__cached_payments[payment_id_int]
            logger.info(f"Payment {payment_id_int} removed from cache.")
        else:
            logger.warning(f"Payment {payment_id_int} not found in cache.")

    def __add_new_payment(self, payment: Payment):
        """
        Adds a new payment to the cache.
        """
        self.__cached_payments[payment.id] = payment
        logger.info(f"Payment for reservation {payment.id} added to cache.")

    def get_payment_by_id(self, payment_id: Union[str, int]) -> Payment:
        """
        Retrieves a payment by its ID from the cache.
        """
        payment_id_int = int(payment_id) if isinstance(payment_id, str) else payment_id
        return self.__cached_payments.get(payment_id_int)

def create_flask_app(external_payment_svc: ExternalPaymentSvc) -> Flask:

    app = Flask(__name__)

    @app.route("/external/generate_payment_link", methods=["POST"])
    def payment_link():
        """
        Generates a payment link for a reservation.
        Args:
            JSON body with:
                Payment object info

        Returns:
            Response: JSON object containing:
                - message (str): Message from payment service in case of success.
                - payment_link (str): An external link to the payment page.
                - reservation_id (str): Unique identifier for the created reservation.
        """
        payment = Payment(**request.json)
        response, code = external_payment_svc.generate_payment_link(payment)
        return jsonify(response), code

    @app.route("/external/payment_link", methods=["GET"])
    def payment_link_clicked():
        """
        Handles when a payment link is clicked and processes the payment.
        """
        payment_id = request.args.get("payment_id")

        if not payment_id:
            return jsonify({"error": "Missing payment_id"}), 400
        
        payment = external_payment_svc.get_payment_by_id(payment_id)
        if not payment:
            return jsonify({"error": "Payment not found"}), 404
        
        
        logger.info(f"Payment link clicked id: {payment_id}")
        
        # Start payment processing in a separate thread
        Thread(target=external_payment_svc.process_payment, args=(payment,), daemon=True).start()
        
        return jsonify({
            "message": "Payment is being processed...", 
            "status": payment.status,
        }), 200
    
    return app

def main():
    external_payment_svc = ExternalPaymentSvc()

    app = create_flask_app(external_payment_svc)
    
    logger.info(
        f"Starting External Payment Service on 'http://{config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_HOST}:{config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_PORT}'"
    )
    app.run(
        host=config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_HOST,
        port=config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_PORT,
        debug=config.DEBUG,
    )
