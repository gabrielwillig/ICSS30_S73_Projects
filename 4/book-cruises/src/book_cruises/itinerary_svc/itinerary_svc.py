import inject
from flask import Flask, request, jsonify

from book_cruises.commons.utils import config, logger
from book_cruises.commons.domains import ItineraryDTO, Itinerary
from book_cruises.commons.domains.repositories import ItineraryRepository
from .di import configure_dependencies

class ItinerarySvc:
    @inject.autoparams()
    def __init__(self):
        self.__itinerary_repository: ItineraryRepository = ItineraryRepository()

    def get_itineraries(self, itinerary_dto: ItineraryDTO) -> list[Itinerary]:
        try:
            return self.__itinerary_repository.get_itineraries(itinerary_dto)

        except Exception as e:
            logger.error(f"Failed to process message: {e}")


def create_flask_app(itinerary_svc: ItinerarySvc) -> Flask:
    app = Flask(__name__)

    @app.route("/itinerary/get-itineraries", methods=["POST"])
    def get_itineraries():

        itinerary_dto = ItineraryDTO(**request.json)
        itineraries = itinerary_svc.get_itineraries(itinerary_dto)

        serialized_itineraries = [itinerary.model_dump() for itinerary in itineraries]
        return jsonify(serialized_itineraries), 200

    return app


def main():
    configure_dependencies()

    itinerary_svc = ItinerarySvc()
    app = create_flask_app(itinerary_svc)
    app.run(
        host=config.ITINERARY_SVC_WEB_SERVER_HOST,
        port=config.ITINERARY_SVC_WEB_SERVER_PORT,
        debug=config.DEBUG,
    )
