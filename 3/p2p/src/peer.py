import uuid
import threading
import Pyro5.api

@Pyro5.api.expose
class Peer:
    def __init__(self):
        self.__id = str(uuid.uuid4())
        self.__name = f"peer-{self.__id}"
        self.__is_tracker = False

    def __register_peer_ns(self, peer_name, uri) -> None:
        """Register the peer with the Pyro name server"""
        ns = Pyro5.api.locate_ns()
        uri = ns.register(peer_name, uri)
        print(f"Peer registered with URI: {uri}")

    def __create_server_thread(self) -> threading.Thread:
        """Start the Pyro server"""
        daemon = Pyro5.server.Daemon()
        try:
            uri = daemon.register(self)
            self.__register_peer_ns(self.__name, uri)
            print(f"Server with name: {self.__name} is running and registered with URI: {uri}")

            return threading.Thread(target=daemon.requestLoop())
        finally:
            self.shutdown()
            print("Server is shutting down.")
    
    def __get_tracker_uri(self):
        """Get the URI of the tracker"""
        ns = Pyro5.api.locate_ns()
        try:
            uri = ns.lookup("tracker")
            return uri
        except Pyro5.errors.PyroError as e:
            print(f"Error looking up tracker: {e}")
            return None

    def __peer_loop(self):
        """Background thread that periodically checks the tracker"""
        while True:
            # TODO: Check the tracker
            if not self.__tracker_uri:
                self.__tracker_uri = self.__get_tracker_uri()

            if self.__is_tracker:
                self.__tracker_loop()
    
    def __tracker_loop(self):
        pass
            
    def __loop_condition(self):
        return True

    def start_peer(self):
        """Start the Pyro daemon and tracker checker thread"""
        server_thread = self.__create_server_thread()
        server_thread.start()

        self.__peer_loop()


if __name__ == "__main__":
    peer = Peer()  # Check every 30 seconds
    peer.start_peer()
