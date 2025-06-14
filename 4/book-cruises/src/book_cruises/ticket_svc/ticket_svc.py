import time

import inject

from book_cruises.commons.utils import config, logger
from book_cruises.commons.messaging import Consumer, Producer
from book_cruises.commons.domains import Payment, Ticket
from .di import configure_dependencies


class TicketSvc:
    @inject.autoparams()
    def __init__(self, consumer: Consumer, producer: Producer):
        self.__consumer: Consumer = consumer
        self.__producer: Producer = producer

    def __process_ticket(self, payment: Payment) -> None:

        if payment.status != "approved":
            logger.error(f"Error processing ticket with data: '{payment.model_dump()}'")
            return

        logger.info(f"Processing approved ticket with payment data: '{payment.model_dump()}'")

        ticket: Ticket = Ticket.create_ticket(payment)

        self.__producer.publish(
            config.TICKET_GENERATED_QUEUE,
            ticket.model_dump(),
        )
        logger.info(f"Ticket generated with data: '{ticket}'")


    def run(self):
        logger.info("Ticket Service Initialized")

        self.__consumer.register_callback(config.APPROVED_PAYMENT_TICKET_QUEUE, self.__process_ticket)
        while True:
            try:
                self.__consumer.start_consuming()
            except Exception as e:
                logger.error(f"Error in thread_consumer", exc_info=True)
                time.sleep(5)


def main() -> None:
    configure_dependencies()

    ticket_svc = TicketSvc()
    ticket_svc.run()
