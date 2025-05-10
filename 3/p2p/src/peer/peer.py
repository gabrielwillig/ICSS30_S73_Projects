import Pyro5.api
import Pyro5.errors
import threading
import time
import random
import sys
from collections import defaultdict
from .logging import logger

Pyro5.config.COMMTIMEOUT = 1.5     


class Peer:
    def __init__(self, name):
        self.name = name
        self.files_index = defaultdict(set)  # Usado para rastrear arquivos
        self.files = set()
        self.current_tracker = None
        self.uri = None
        self.tracker_epoch = 0
        self.voted_in_epoch = -1
        self.election_in_progress = False
        self.peers = {}
        self.heartbeat_timer = None
        self.election_timer = None
        self.lock = threading.Lock()

    def register_with_nameserver(self, uri):
        try:
            with Pyro5.api.locate_ns() as ns:
                ns.register(f"Peer_{self.name}", uri)
                logger.info(f"Peer {self.name} registrado no serviço de nomes")
                # Tentar encontrar o tracker atual
                self.find_current_tracker()
        except Pyro5.errors.NamingError:
            logger.error("Serviço de nomes não encontrado. Iniciando sem tracker.")

    def find_current_tracker(self):
        try:
            with Pyro5.api.locate_ns() as ns:
                tracker_list = ns.list(prefix="Tracker_Epoca")
                if tracker_list:
                    # Pegar o tracker com a época mais recente
                    latest_epoch = max(int(name.split("_")[-1]) for name in tracker_list.keys())
                    tracker_uri = ns.lookup(f"Tracker_Epoca_{latest_epoch}")
                    self.current_tracker = Pyro5.api.Proxy(tracker_uri)
                    self.tracker_epoch = latest_epoch
                    logger.info(f"Tracker encontrado (Época {self.tracker_epoch})")

                    # Registrar arquivos no tracker
                    self.register_files_with_tracker()

                    # Iniciar heartbeat
                    self.start_heartbeat_listener()
        except Pyro5.errors.NamingError:
            logger.error("Nenhum tracker encontrado no serviço de nomes")

    def register_files_with_tracker(self):
        if self.current_tracker:
            try:
                self.current_tracker.register_files(self.name, list(self.files))
                logger.info(f"Arquivos registrados no tracker: {self.files}")
            except Pyro5.errors.CommunicationError:
                logger.error("Falha ao registrar arquivos no tracker")
                self.current_tracker = None

    def add_file(self, filename):
        with self.lock:
            self.files.add(filename)
            if self.current_tracker:
                try:
                    self.current_tracker.add_file(self.name, filename)
                except Pyro5.errors.CommunicationError:
                    logger.error("Falha ao atualizar arquivo no tracker")

    def remove_file(self, filename):
        with self.lock:
            if filename in self.files:
                self.files.remove(filename)
                if self.current_tracker:
                    try:
                        self.current_tracker.remove_file(self.name, filename)
                    except Pyro5.errors.CommunicationError:
                        logger.error("Falha ao remover arquivo no tracker")

    def start_heartbeat_listener(self):
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()

        self.heartbeat_timer = threading.Timer(self.get_random_timeout(), self.initiate_election)
        self.heartbeat_timer.start()

    def get_random_timeout(self):
        return random.uniform(0.15, 0.3)  # 150-300ms

    def reset_tracker_timer(self):
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
        self.heartbeat_timer = threading.Timer(self.get_random_timeout(), self.initiate_election)
        self.heartbeat_timer.start()

    def initiate_election(self):
        with self.lock:
            if self.election_in_progress:
                return

            self.election_in_progress = True
            self.tracker_epoch += 1
            self.voted_in_epoch = self.tracker_epoch
            votes_received = 0
            total_votes = 0
            
            votes_received += 1  # Vota em si mesmo
            total_votes += 1

            logger.info(f"Iniciando eleição para Época {self.tracker_epoch}")

            # Buscar todos os peers conhecidos
            try:
                with Pyro5.api.locate_ns() as ns:
                    peer_list = ns.list(prefix="Peer")
                    for name, uri in peer_list.items():
                        if name != f"Peer_{self.name}":
                            match self.request_vote(uri):
                                case "accepted":
                                    total_votes += 1
                                    votes_received += 1
                                    logger.info(f"Voto recebido de {name}")
                                case "refused":
                                    total_votes += 1
                                    logger.info(f"Voto negado por {name}")
                                case _:
                                    logger.info(f"Falha ao solicitar voto de {name}")
                                    
                if self.is_elected(total_votes, votes_received):
                    self.become_tracker()           
                         
            except Pyro5.errors.NamingError:
                logger.error("Serviço de nomes não disponível durante eleição")

    def request_vote(self, uri):
        peer = Pyro5.api.Proxy(uri)
        logger.debug(f"Solicitando voto de {uri}")
        try:
            return peer.vote(self.tracker_epoch, self.name)
        except Exception as e:
            logger.error(f"{e} :: Falha ao solicitar voto de {uri}")
    
    @Pyro5.api.expose
    def vote(self, epoch, candidate_name):
        if epoch > self.voted_in_epoch:
            self.voted_in_epoch = epoch
            logger.info(f"Voto concedido para {candidate_name} na Época {epoch}")
            return "accepted"
        logger.warning(f"Voto negado para {candidate_name} na Época {epoch}. Já votei na Época {self.voted_in_epoch}")
        return "refused"
    
    def is_elected(self, total_votes, votes_received):
        """Computa o quorum de votos recebidos"""
        if votes_received >= total_votes // 2 + 1:
            return True
        return False

    def become_tracker(self):
        logger.info(f"Eleito como tracker para Época {self.tracker_epoch}")
        self.current_tracker = self
        self.election_in_progress = False

        # Registrar como tracker no serviço de nomes
        try:
            with Pyro5.api.locate_ns() as ns:
                ns.register(f"Tracker_Epoca_{self.tracker_epoch}", self.uri)
                logger.info(f"Registrado como tracker no serviço de nomes (Época {self.tracker_epoch})")
        except Pyro5.errors.NamingError:
            logger.error("Falha ao registrar como tracker no serviço de nomes")

        # Notificar outros peers sobre o novo tracker
        self.notify_peers()

        # Iniciar envio de heartbeats
        self.start_heartbeat_sender()

    def notify_peers(self):
        try:
            with Pyro5.api.locate_ns() as ns:
                peer_list = ns.list(prefix="Peer")
                for name, uri in peer_list.items():
                    if name != f"Peer_{self.name}":
                        peer = Pyro5.api.Proxy(uri)
                        try:
                            peer.update_tracker(self.tracker_epoch, self.uri)
                        except Pyro5.errors.CommunicationError:
                            logger.warning(f"Falha ao notificar {name}")
        except Pyro5.errors.NamingError:
            logger.error("Serviço de nomes não disponível para notificação")

    @Pyro5.api.expose
    def update_tracker(self, epoch, tracker_uri):
        if epoch > self.tracker_epoch:
            self.tracker_epoch = epoch
            self.current_tracker = Pyro5.api.Proxy(tracker_uri)
            self.voted_in_epoch = -1
            self.reset_tracker_timer()

            # Registrar arquivos com o novo tracker
            self.register_files_with_tracker()

    def start_heartbeat_sender(self):
        if hasattr(self, "heartbeat_sender") and self.heartbeat_sender.is_alive():
            self.heartbeat_sender.cancel()

        self.heartbeat_sender = threading.Timer(0.1, self.send_heartbeat)  # 100ms
        self.heartbeat_sender.start()

    def send_heartbeat(self):
        try:
            with Pyro5.api.locate_ns() as ns:
                peer_list = ns.list(prefix="Peer")
                for name, uri in peer_list.items():
                    if name != f"Peer_{self.name}":
                        peer = Pyro5.api.Proxy(uri)
                        try:
                            peer.heartbeat_received()
                        except Pyro5.errors.CommunicationError:
                            pass
        except Pyro5.errors.NamingError:
            logger.error("Serviço de nomes não disponível para enviar heartbeats")

        self.start_heartbeat_sender()

    @Pyro5.api.expose
    @Pyro5.api.oneway
    def heartbeat_received(self):
        self.reset_tracker_timer()

    # Métodos do tracker
    # For tracker functionality (when peer becomes tracker)
    @Pyro5.api.expose
    def register_files(self, peer_name, files):
        """Tracker method to register files from a peer"""
        with self.lock:
            for filename in files:
                if filename not in self.files_index:  # files_index is a defaultdict(set)
                    self.files_index[filename] = set()
                self.files_index[filename].add(peer_name)

    @Pyro5.api.expose
    def add_file(self, peer_name, filename):
        """Tracker method to add a single file from a peer"""
        with self.lock:
            self.files_index[filename].add(peer_name)

    @Pyro5.api.expose
    def remove_file(self, peer_name, filename):
        with self.lock:
            if filename in self.files and peer_name in self.files[filename]:
                self.files[filename].remove(peer_name)
                if not self.files[filename]:
                    del self.files[filename]

    @Pyro5.api.expose
    def get_file_locations(self, filename):
        with self.lock:
            return list(self.files.get(filename, set()))

    # Métodos P2P
    @Pyro5.api.expose
    def request_file(self, filename, peer_name):
        """Método chamado por outro peer para solicitar um arquivo"""
        if filename in self.files:
            # Simular transferência de arquivo
            logger.info(f"Enviando arquivo {filename} para {peer_name}")
            return f"Conteúdo do arquivo {filename}"
        raise Pyro5.errors.CommunicationError(f"Arquivo {filename} não encontrado")

    def download_file(self, filename):
        """Método para baixar um arquivo da rede P2P"""
        if not self.current_tracker:
            logger.warning("Nenhum tracker disponível")
            return

        try:
            # Consultar tracker
            providers = self.current_tracker.get_file_locations(filename)
            if not providers:
                logger.warning(f"Arquivo {filename} não encontrado na rede")
                return

            # Escolher um provedor aleatório
            provider_name = random.choice(providers)
            if provider_name == self.name:
                logger.warning("Você já possui este arquivo")
                return

            # Conectar ao peer e solicitar arquivo
            with Pyro5.api.locate_ns() as ns:
                provider_uri = ns.lookup(f"Peer_{provider_name}")
                provider = Pyro5.api.Proxy(provider_uri)
                content = provider.request_file(filename, self.name)

                # Salvar arquivo localmente
                self.add_file(filename)
                logger.info(f"Arquivo {filename} baixado com sucesso de {provider_name}")
                return content
        except Pyro5.errors.CommunicationError as e:
            logger.error(f"Falha ao baixar arquivo: {e}")

    def start_peer(self):
        """Inicia o peer e registra no serviço de nomes"""
        daemon = Pyro5.api.Daemon()
        self.uri = daemon.register(self)
        self.register_with_nameserver(self.uri)  # Registrar no serviço de nomes
        self.reset_tracker_timer()  # Iniciar o timer de heartbeat
        logger.info(f"Peer {self.name} iniciado com URI: {self.uri}")

        # Adicionar alguns arquivos fictícios
        for i in range(3):
            self.add_file(self.name, f"arquivo_{self.name}_{i}.txt")

        threading.Thread(target=daemon.requestLoop, daemon=True).start()
        return self


def main():
    if len(sys.argv) < 2:
        logger.info("Uso: python peer.py <nome_peer>")
        sys.exit(1)

    peer_name = sys.argv[1]
    peer = Peer(peer_name)
    peer.start_peer()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.error("Encerrando peer...")
