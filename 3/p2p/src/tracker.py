from .peer import Peer

class Tracker(Peer):
    def __init__(self, tracker_check_interval=30):
        super().__init__(tracker_check_interval)
        self.__is_tracker = True