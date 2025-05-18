import os
import sys
import socket
import inquirer
import threading

import Pyro5.api
import Pyro5.errors

from collections import defaultdict

from .logging import logger
from .utils import generate_random_text_file

def get_my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't actually connect, just finds the outbound IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


PEER_HOSTNAME = get_my_ip()  # ou o IP do peer
NAMESERVER_HOSTNAME = os.getenv("PYRO_NS_HOSTNAME")

TRACKER_HEARTBEAT_INTERVAL = 1  # 100ms
# RAND_TIME_INTERVAL = [15, 30]  # 150ms - 300ms

TIME_MAP = {
    "peer-1": 1.5,
    "peer-2": 2.0,
    "peer-3": 2.5,
    "peer-4": 3.0,
    "peer-5": 3.5,
}

Pyro5.config.COMMTIMEOUT = 0.1  # Timeout for Pyro calls


class Peer:
    def __init__(self, name):
        self.name = name
        self.files_index = defaultdict(set)  # Usado para rastrear arquivos, apenas tracker o possui
        self.files = set() # Usado para rastrear arquivos, apenas o peer possui
        self.current_tracker_uri = None
        self.uri = None
        self.tracker_epoch = 0
        self.voted_in_epoch = -1
        self.election_in_progress = False
        self.peers = {}
        self.heartbeat_timer = None
        self.election_timer = None
        # self.lock = threading.Lock()

    def get_tracker_proxy(self, uri):
        return Pyro5.api.Proxy(uri)

    def get_tracker_uri(self, epoch):
        with Pyro5.api.locate_ns(NAMESERVER_HOSTNAME) as ns:
            try:
                return ns.lookup(f"Tracker_Epoca_{epoch}")
            except Pyro5.errors.NamingError:
                logger.error("Falha ao localizar o tracker no serviço de nomes")
                return None

    def register_with_nameserver(self, uri, name):
        try:
            with Pyro5.api.locate_ns(NAMESERVER_HOSTNAME) as ns:
                ns.register(name, uri)
                logger.info(f"Peer {name} registrado no serviço de nomes")
        except Pyro5.errors.NamingError:
            logger.error("Serviço de nomes não encontrado.")

    def find_current_tracker(self):
        try:
            with Pyro5.api.locate_ns(NAMESERVER_HOSTNAME) as ns:
                tracker_list = ns.list(prefix="Tracker_Epoca")
                if tracker_list:
                    # Pegar o tracker com a época mais recente
                    latest_epoch = max(int(name.split("_")[-1]) for name in tracker_list.keys())
                    self.current_tracker_uri = ns.lookup(f"Tracker_Epoca_{latest_epoch}")
                    self.tracker_epoch = latest_epoch
                    logger.info(f"Tracker encontrado (Época {self.tracker_epoch})")

                    # Registrar arquivos no tracker
                    self.register_files_with_tracker()
        except Pyro5.errors.NamingError:
            logger.error("Nenhum tracker encontrado no serviço de nomes")

    def register_files_with_tracker(self):
        if self.current_tracker_uri:
            try:
                tracker_proxy = self.get_tracker_proxy(self.current_tracker_uri)
                tracker_proxy.register_files(self.name, list(self.files))
                #logger.info(f"Arquivos registrados no tracker: {self.files}")
            except Pyro5.errors.CommunicationError:
                logger.error("Falha ao registrar arquivos no tracker")
                self.current_tracker_uri = None

    def add_file(self, filename):
        # with self.lock:
        self.files.add(filename)
        if self.current_tracker_uri:
            try:
                tracker_proxy = self.get_tracker_proxy(self.current_tracker_uri)
                tracker_proxy.register_files(self.name, [filename])
            except Pyro5.errors.CommunicationError:
                logger.error("Falha ao registrar arquivo no tracker")

    def remove_peer_files(self):
        # with self.lock:
        for filename in list(self.files):
            self.files.remove(filename)
            if self.current_tracker_uri:
                try:
                    tracker_proxy = self.get_tracker_proxy(self.current_tracker_uri)
                    tracker_proxy.remove_file(self.name, filename)
                except Pyro5.errors.CommunicationError:
                    logger.error("Falha ao remover arquivo no tracker")

    def get_random_timeout(self):
        return TIME_MAP.get(self.name)

    def reset_tracker_timer(self):
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
        self.heartbeat_timer = threading.Timer(self.get_random_timeout(), self.initiate_election)
        self.heartbeat_timer.start()

    def voted_in_election_check(self):
        return self.voted_in_epoch > self.tracker_epoch

    def initiate_election(self):
        # with self.lock:
        if self.election_in_progress:
            logger.warning(f"{self.name} | Eleição já em andamento. Ignorando nova eleição.")
            self.reset_tracker_timer()
            return
        elif self.voted_in_election_check():
            logger.warning(f"{self.name} | Época {self.voted_in_epoch} já votada. Ignorando eleição.")
            self.reset_tracker_timer()
            return

        self.election_in_progress = True
        self.tracker_epoch += 1
        self.voted_in_epoch = self.tracker_epoch
        votes_received = 0
        total_votes = 0

        votes_received += 1  # Vota em si mesmo
        total_votes += 1

        logger.info(f"Iniciando eleição para Época {self.tracker_epoch}")

        try:
            with Pyro5.api.locate_ns(NAMESERVER_HOSTNAME) as ns:
                peer_list = ns.list(prefix="Peer")
                for name, uri in peer_list.items():
                    if name != f"Peer_{self.name}":
                        match self.request_vote(uri):
                            case "accepted":
                                total_votes += 1
                                votes_received += 1
                            case "refused":
                                total_votes += 1
                            case _:
                                logger.warning(f"{self.name} falhou ao solicitar voto de {name}")

            if self.is_elected(total_votes, votes_received):
                self.become_tracker()
            else:
                logger.warning(f"Eleição falhou. Votos recebidos: {votes_received}/{total_votes}")
                self.election_in_progress = False
                self.voted_in_epoch = -1
                self.tracker_epoch -= 1
                self.reset_tracker_timer()

        except Pyro5.errors.NamingError:
            logger.error("Serviço de nomes não disponível durante eleição")

    def request_vote(self, uri):
        with self.get_tracker_proxy(uri) as peer:
            try:
                return peer.vote(self.tracker_epoch, self.name)
            except Exception as e:
                logger.error(f"{e} :: Falha ao solicitar voto de {uri}")

    @Pyro5.api.expose
    def vote(self, epoch, candidate_name):
        # with self.lock:
        if epoch > self.voted_in_epoch:
            self.voted_in_epoch = epoch
            logger.info(f"{self.name} votou em {candidate_name} | Época {epoch}")
            return "accepted"
        logger.warning(f"{self.name} negou voto para {candidate_name}. Época {self.voted_in_epoch} já votada")
        return "refused"

    def is_elected(self, total_votes, votes_received):
        """Computa o quorum de votos recebidos"""
        if votes_received >= total_votes // 2 + 1:
            return True
        return False

    def become_tracker(self):
        logger.info(f"Eleito: {self.name} | Época: {self.tracker_epoch}")
        self.current_tracker_uri = self.uri
        self.election_in_progress = False

        # Registrar como tracker no serviço de nomes
        try:
            self.register_with_nameserver(self.uri, f"Tracker_Epoca_{self.tracker_epoch}")
            logger.info(f"{self.name} registrado como tracker no serviço de nomes | Época: {self.tracker_epoch}")
        except Pyro5.errors.NamingError:
            logger.error("Falha ao registrar como tracker no serviço de nomes")

        # Registrar arquivos do peer no tracker
        for file in self.files:
            self.files_index[file].add(self.name)

        # Iniciar envio de heartbeats
        logger.debug("Iniciando envio de heartbeats para peers")
        self.start_heartbeat_sender()

    def start_heartbeat_sender(self):
        if hasattr(self, "heartbeat_sender") and self.heartbeat_sender.is_alive():
            self.heartbeat_sender.cancel()

        self.heartbeat_sender = threading.Timer(TRACKER_HEARTBEAT_INTERVAL, self.send_heartbeat)
        self.heartbeat_sender.start()

    def send_heartbeat(self):
        try:
            with Pyro5.api.locate_ns(NAMESERVER_HOSTNAME) as ns:
                peer_list = ns.list(prefix="Peer")
                for name, uri in peer_list.items():
                    if name != f"Peer_{self.name}":
                        peer = Pyro5.api.Proxy(uri)
                        try:
                            peer.heartbeat_received(self.name, self.tracker_epoch)
                        except Pyro5.errors.CommunicationError:
                            pass
        except Pyro5.errors.NamingError:
            logger.error("Serviço de nomes não disponível para enviar heartbeats")

        self.start_heartbeat_sender()

    @Pyro5.api.expose
    @Pyro5.api.oneway
    def heartbeat_received(self, tracker_name, epoch):
        # logger.debug(
        #     f"Heartbeat received from {tracker_name} | Época {epoch} | Época do meu tracker: {self.tracker_epoch}"
        # )
        if epoch > self.tracker_epoch:
            self.tracker_epoch = epoch
            self.voted_in_epoch = -1
            with Pyro5.api.locate_ns(NAMESERVER_HOSTNAME) as ns:
                tracker_uri = ns.lookup(f"Tracker_Epoca_{epoch}")
                self.current_tracker_uri = tracker_uri
            logger.info(f"Atualizando tracker para {tracker_name} | Época {epoch}")
            self.register_files_with_tracker()
            #threading.Thread(target=self.register_files_with_tracker).start()

        self.reset_tracker_timer()

    # Métodos do tracker
    # For tracker functionality (when peer becomes tracker)
    @Pyro5.api.expose
    def register_files(self, peer_name, files):
        """Tracker method to register files from a peer"""
        # with self.lock:
        logger.debug(f"Registrando arquivos do peer {peer_name}")
        for filename in files:
            if filename not in self.files_index:  # files_index is a defaultdict(set)
                self.files_index[filename] = set()
            self.files_index[filename].add(peer_name)

    # @Pyro5.api.expose
    # def add_file(self, peer_name, filename):
    #     """Tracker method to add a single file from a peer"""
    #     # with self.lock:
    #     self.files_index[filename].add(peer_name)

    @Pyro5.api.expose
    def remove_file(self, peer_name, filename):
        # with self.lock:
        if filename in self.files_index and peer_name in self.files_index[filename]:
            self.files_index[filename].remove(peer_name)
            if not self.files_index[filename]:
                del self.files_index[filename]

    @Pyro5.api.expose
    def get_file_locations(self, filename):
        # with self.lock:
        return list(self.files.get(filename, set()))

    # Métodos P2P
    @Pyro5.api.expose
    def request_file(self, filename, peer_name):
        """Método chamado por outro peer para solicitar um arquivo"""
        if filename in list(self.files):
            filepath = os.path.join(os.getcwd(), self.name, filename)
            if not os.path.isfile(filepath):
                logger.warning(f"Arquivo {filename} não encontrado no peer {self.name}")
                return None
            # Simular transferência de arquivo
            logger.info(f"Enviando arquivo {filename} de {peer_name}")
            with open(filepath, "r") as f:
                content = f.read()
            return content
        raise Pyro5.errors.CommunicationError(f"Arquivo {filename} não encontrado")

    @Pyro5.api.expose
    def list_files(self):
        """Método para listar arquivos disponíveis no peer"""
        return list(self.files_index.keys())

    @Pyro5.api.expose
    def list_peers_with_file(self, filename):
        """Método para listar peers que possuem um arquivo específico"""
        if filename in self.files_index:
            return list(self.files_index[filename])
        return []

    def download_file(self, filename, peer_name):
        """Método para baixar um arquivo da rede P2P"""
        if not self.current_tracker_uri:
            logger.warning("Nenhum tracker disponível")
            return

        try:
            if filename in self.files:
                logger.warning("Você já possui este arquivo")
                return

            # Conectar ao peer e solicitar arquivo
            with Pyro5.api.locate_ns(NAMESERVER_HOSTNAME) as ns:
                provider_uri = ns.lookup(f"Peer_{peer_name}")
                provider = Pyro5.api.Proxy(provider_uri)
                content = provider.request_file(filename, self.name)

                # Salvar arquivo localmente
                self.add_file(filename)
                logger.info(f"Arquivo {filename} baixado com sucesso de {peer_name}")                return content
        except Pyro5.errors.CommunicationError as e:
            logger.error(f"Falha ao baixar arquivo: {e}")

    def start_random_files(self):
        for i in range(3):
            filename = f"arquivo_{self.name}_{i}.txt"
            filepath = os.path.join(os.getcwd(), self.name, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            generate_random_text_file(filepath, size=128)
            self.add_file(filename) # Add file index

    def start_peer(self):
        """Inicia o peer e registra no serviço de nomes"""
        # Adicionar alguns arquivos fictícios

        daemon = Pyro5.api.Daemon(host=PEER_HOSTNAME)
        self.uri = daemon.register(self)
        logger.info(f"Peer {self.name} iniciado com URI: {self.uri}")
        self.register_with_nameserver(self.uri, f"Peer_{self.name}")  # Registrar no serviço de nomes

        self.start_random_files()

        self.find_current_tracker()

        self.reset_tracker_timer()  # Iniciar o timer de heartbeat

        t = threading.Thread(target=daemon.requestLoop, daemon=True)
        t.start()

def interactive_cli(peer: Peer):
    files = []
    try:
        while True:
            choice = inquirer.list_input(
                message="O que deseja fazer?",
                choices=["Atualizar lista de arquivos", "Baixar Arquivo"],
            )
            tracker = Pyro5.api.Proxy(peer.current_tracker_uri)
            if choice == "Atualizar lista de arquivos":
                files = tracker.list_files()
                if files:
                    print("Arquivos disponíveis:")
                    for i, file in enumerate(files):
                        print(f"{i + 1}. {file}")
                else:
                    print("Nenhum arquivo disponível.")
            elif choice == "Baixar Arquivo":
                file_to_download = inquirer.list_input(
                    message="Selecione um arquivo para baixar",
                    choices=files,
                )
                peers_with_file = tracker.list_peers_with_file(file_to_download)
                download_from_peer = inquirer.list_input(
                    message="Selecione de qual peer baixar",
                    choices=peers_with_file,
                )
                content = peer.download_file(file_to_download, download_from_peer)
                if content:
                    filepath = os.path.join(os.getcwd(), peer.name, file_to_download)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    with open(filepath, "w") as f:
                        f.write(content)
                else:
                    print(f"Falha ao baixar o arquivo {file_to_download} de {download_from_peer}")
    except KeyboardInterrupt:
        logger.info("Encerrando CLI interativa...")
        peer.remove_peer_files()
        sys.exit(0)

def main():
    if len(sys.argv) < 2:
        logger.info("Uso: python peer.py <nome_peer>")
        sys.exit(1)
    peer_name = sys.argv[1]
    peer = Peer(peer_name)
    peer.start_peer()
    interactive_cli(peer)