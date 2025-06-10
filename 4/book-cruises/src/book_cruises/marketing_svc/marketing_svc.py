import inject
import random
import time
import threading
from datetime import datetime, date
from book_cruises.commons.utils import logger, config
from book_cruises.commons.messaging import Producer
from book_cruises.commons.database import Database
from .di import configure_dependencies  

class MarketingSvc:
    @inject.autoparams()
    def __init__(self, producer: Producer, database: Database):
        self.__producer: Producer = producer
        self.__database: Database = database
        self.__running = False
        self.__promotion_thread = None
        self.__destinations = []
    
    def __get_available_destinations(self):
        """Fetch unique destinations from database"""
        try:
            query = "SELECT DISTINCT arrival_harbor FROM itineraries"
            results = self.__database.execute_query(query)
            
            if not results:
                raise Exception("No destinations found in the database")
                
            self.__destinations = [row["arrival_harbor"] for row in results]
            logger.info(f"Found {len(self.__destinations)} destinations: {self.__destinations}")
        except Exception as e:
            logger.error(f"Error retrieving destinations: {e}")
            self.__destinations = ["Miami", "Nassau", "San Juan", "Kingston", "Havana"]  # Default set
    
    def __get_random_itinerary(self, destination):
        """Get a random itinerary for a specific destination"""
        try:
            query = f"""
                SELECT * FROM itineraries 
                WHERE LOWER(arrival_harbor) = LOWER('{destination}')
                ORDER BY RANDOM() LIMIT 1
            """
            results = self.__database.execute_query(query)
            
            if results and len(results) > 0:
                return results[0]
            return None
        except Exception as e:
            logger.error(f"Error getting random itinerary for {destination}: {e}")
            return None
    
    def __generate_promotion(self, destination):
        """Generate a promotion for a destination"""
        itinerary = self.__get_random_itinerary(destination)
        
        if not itinerary:
            logger.warning(f"No itineraries found for destination: {destination}")
            return None
            
        discount = random.randint(10, 40)  # Random discount between 10% and 40%
        expires_in = random.randint(1, 24)  # Random expiry time 1-24 hours
        
        # Handle date serialization properly
        departure_date = itinerary["departure_date"]
        if isinstance(departure_date, datetime):
            formatted_date = departure_date.strftime("%Y-%m-%d")
        elif isinstance(departure_date, date):
            formatted_date = departure_date.strftime("%Y-%m-%d")
        else:
            formatted_date = str(departure_date)
        
        promotion = {
            "title": f"Special Offer to {destination}!",
            "description": f"Limited time cruise deal to {destination} on {itinerary['ship']}",
            "destination": destination,
            "itinerary_id": itinerary["id"],
            "discount": discount,
            "expires_in": f"{expires_in} hours",
            "original_price": float(itinerary["price"]),
            "discounted_price": round(float(itinerary["price"]) * (1 - discount/100), 2),
            "departure_date": formatted_date,
            "timestamp": datetime.now().isoformat()
        }
        
        return promotion
    
    def __promotion_generator_loop(self):
        """Background thread to continuously generate promotions"""
        while self.__running:
            # Pick a random destination
            if not self.__destinations:
                self.__get_available_destinations()
                
            if self.__destinations:
                destination = random.choice(self.__destinations)
                
                # Generate promotion
                promotion = self.__generate_promotion(destination)

                routing_key = destination.lower().replace(" ", "_")
                
                if promotion:
                    # Publish to destination-specific queue
                    logger.info(f"Publishing promotion for {destination}: {promotion['discount']}% off")
                    self.__producer.publish(
                        routing_key=routing_key,
                        message=promotion,
                        exchange=config.PROMOTIONS_EXCHANGE
                    )
                
            # Wait before generating next promotion (5-15 seconds)
            time.sleep(random.uniform(5, 15))

    def __delete_exchange(self):
        """Purge all promotion queues created by this service"""
        # Ensure channel is ready
        self.__producer._ensure_channel()
        
        try:
            logger.info(f"Deleting marketing exchange: {config.PROMOTIONS_EXCHANGE}")
            self.__producer.channel.exchange_delete(exchange=config.PROMOTIONS_EXCHANGE)
        except Exception as e:
            logger.error(f"Error deleting exchange {config.PROMOTIONS_EXCHANGE}: {e}")
        
    def run(self):
        """Start the marketing service"""
        logger.info("Marketing Service initialized")
        
        # Initialize database connection
        self.__database.initialize()
        
        # Get available destinations
        self.__get_available_destinations()
        
        # Declare a queue for each destination
        self.__producer._ensure_channel()
        self.__producer.channel.exchange_declare(exchange=config.PROMOTIONS_EXCHANGE, exchange_type="topic")
        logger.info(f"Declared promotion exchange: {config.PROMOTIONS_EXCHANGE}")
        
        # Start promotion generator thread
        self.__running = True
        self.__promotion_thread = threading.Thread(target=self.__promotion_generator_loop)
        self.__promotion_thread.daemon = True
        self.__promotion_thread.start()
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down Marketing Service...")
            self.__running = False
            if self.__promotion_thread:
                self.__promotion_thread.join(timeout=2)
            
            # Clean up by purging all promotion queues
            self.__delete_exchange()
            logger.info("Marketing Service shutdown complete")


def main() -> None:
    """Entry point for the marketing service"""
    configure_dependencies()
    
    marketing_svc = MarketingSvc()
    marketing_svc.run()