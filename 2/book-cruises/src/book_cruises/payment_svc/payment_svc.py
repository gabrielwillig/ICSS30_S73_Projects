import inject
import json
import random  
from book_cruises.commons.utils import config, logger
from book_cruises.commons.messaging import Consumer, Producer
from .di import configure_dependencies  


class PaymentSvc:
    @inject.autoparams()
    def __init__(self, consumer: Consumer, producer: Producer):
        self.__consumer: Consumer = consumer
        self.__producer: Producer = producer
    
    def __process_payment(self, payment_data: dict) -> None:
        logger.info(f"Processing payment with data: {payment_data}")
        
        # Simulate random success or failure
        if random.choice([True, False]):  # Randomly choose True (success) or False (failure)
            logger.info("Payment approved")
            self.__producer.publish(
                config.APPROVED_PAYMENT_QUEUE,
                json.dumps({"status": "approved", "payment_data": payment_data}),
            )
        else:
            logger.info("Payment refused")
            self.__producer.publish(
                config.REFUSED_PAYMENT_QUEUE,
                json.dumps({"status": "refused", "payment_data": payment_data}),
            )

    def run(self):
        logger.info("Payment Service initialized")
        self.__consumer.declare_queue(config.APPROVED_PAYMENT_QUEUE, durable=False)
        self.__consumer.declare_queue(config.REFUSED_PAYMENT_QUEUE, durable=False)
        
        self.__consumer.register_callback(config.RESERVE_CREATED_QUEUE, self.__process_payment)
        self.__consumer.start_consuming()


def main() -> None:
    configure_dependencies()

    payment_svc = PaymentSvc()
    payment_svc.run()
