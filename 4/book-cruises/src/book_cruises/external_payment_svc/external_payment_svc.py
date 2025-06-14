import time
from threading import Thread
import random
import requests
from flask import Flask, request, jsonify

from book_cruises.commons.utils import config, logger
from book_cruises.commons.domains import Payment

PROCESSING_DELAY = 6  # seconds

app = Flask(__name__)


@app.route("/external/receives-payment", methods=["POST"])
def receives_payment():
    payment: Payment = Payment(**request.json)
    logger.info(f"Received payment: {payment.model_dump()}")

    Thread(target=process_payment, args=(payment,), daemon=True).start()

    return jsonify({"message": "External payment service is processing..."}), 200


def process_payment(payment: Payment):
    """
    Simulates processing a payment and calls a webhook indicating whether the payment was approved or refused.
    """
    logger.info("External service processing payment...")

    # Simulate a delay to mimic real-world processing time
    time.sleep(PROCESSING_DELAY)

    if random.choice([True]):
        payment.status = "approved"
        logger.info("Payment approved")
    else:
        payment.status = "refused"
        logger.warning("Payment refused")

    webhook_url = f"http://{config.PAYMENT_SVC_WEB_SERVER_HOST}:{config.PAYMENT_SVC_WEB_SERVER_PORT}/payment/notify"
    requests.post(
        webhook_url, json=payment.model_dump(), timeout=config.REQUEST_TIMEOUT
    )


def main():
    logger.info(
        f"Starting External Payment Service on 'http://{config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_HOST}:{config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_PORT}'"
    )
    app.run(
        host=config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_HOST,
        port=config.EXTERNAL_PAYMENT_SVC_WEB_SERVER_PORT,
        debug=config.DEBUG,
    )
