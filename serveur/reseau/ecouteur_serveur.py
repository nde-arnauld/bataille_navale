import socket
import threading
import time

from commun import constantes as const
from .gestionnaire_client import GestionnaireClient
from ..donnees.gestionnaire_utilisateur import GestionnaireUtilisateur
from ..logique_jeu.gestionnaire_partie import GestionnairePartie


class EcouteurServeur(threading.Thread):
    """
    Thread d'écoute principal du serveur. 
    Gère l'acceptation des connexions TCP entrantes et lance un GestionnaireClient 
    pour chaque nouvelle connexion.
    """

    def __init__(self, gestionnaire_utilisateurs: GestionnaireUtilisateur, gestionnaire_partie: GestionnairePartie, host: str = const.SERVEUR, port: int = const.PORT_JEU):
        super().__init__()
        # Écoute sur toutes les interfaces réseau
        self.host = host if host != const.SERVEUR else '0.0.0.0'
        self.port = port
        self.gestionnaire_utilisateurs = gestionnaire_utilisateurs
        self.socket_tcp: socket.socket | None = None
        self.clients_actifs: list[GestionnaireClient] = []
        self.actif = True
        self.gestionnaire_partie = gestionnaire_partie  # Nouvelle référence injectée
        self.clients_connectes_map: dict[str, GestionnaireClient] = {}  # Map Nom -> Thread Client
        self.map_lock = threading.Lock()

    def run(self):
        """ 
        Initialise le socket TCP et entre dans la boucle d'acceptation de connexions.
        """
        try:
            # 1. Création et liaison du socket TCP
            self.socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket_tcp.bind((self.host, self.port))

            # 2. Mise en écoute (const.NB_MAX_CONNEXIONS est le nombre max de connexions en attente)
            self.socket_tcp.listen(const.NB_MAX_CONNEXIONS)
            print(f"TCP Écouteur Serveur: Prêt. Attente de connexions sur {self.host}:{self.port}")

            while self.actif:
                # 3. Nettoyage des threads client terminés
                self._nettoyer_clients()

                try:
                    # Accepter une nouvelle connexion (bloquant)
                    connexion_client, adresse_client = self.socket_tcp.accept()
                    print(f"TCP Écouteur Serveur: Nouvelle connexion de {adresse_client[0]}:{adresse_client[1]}")

                    # 4. Créer et lancer le gestionnaire de ce client
                    # Lorsqu'on vient d'entrer ConnecteurClient.connecter_tcp()
                    # Toute cette partie est initialisée.
                    gestionnaire = GestionnaireClient(
                        connexion_client,
                        adresse_client,
                        self.gestionnaire_utilisateurs,
                        self.gestionnaire_partie
                    )

                    # NOTE: L'enregistrement dans la map sera fait par le GestionnaireClient
                    # Dans sa méthode _initialiser_session après avoir reçu le nom.
                    # Cependant, nous avons besoin d'une fonction pour qu'il s'enregistre et se désenregistre.

                    gestionnaire.set_callbacks(self.enregistrer_client, self.desenregistrer_client)
                    self.clients_actifs.append(gestionnaire)
                    gestionnaire.start()

                except socket.error as e:
                    # Erreur attendue lors de l'arrêt si le socket est fermé
                    if self.actif:
                        print(f"TCP Écouteur Serveur Erreur d'acceptation: {e}")
                    # Quitter si le socket a été fermé par stop()
                    break
                except Exception as e:
                    print(f"TCP Écouteur Serveur Erreur inattendue: {e} -- run() ecouteur_serveur")

                # Petite pause pour éviter une boucle trop agressive
                time.sleep(0.1)

        except Exception as e:
            print(f"TCP Écouteur Serveur Échec de l'initialisation du serveur: {e}")
        finally:
            if self.socket_tcp:
                self.socket_tcp.close()
            print("TCP Écouteur Serveur: Arrêté.")

    def enregistrer_client(self, nom_joueur: str, client_instance: 'GestionnaireClient') -> None:
        with self.map_lock:
            self.clients_connectes_map[nom_joueur] = client_instance
            print(f"Écouteur Serveur: {nom_joueur} enregistré dans la map.")

    def desenregistrer_client(self, nom_joueur: str) -> None:
        with self.map_lock:
            if nom_joueur in self.clients_connectes_map:
                del self.clients_connectes_map[nom_joueur]
                print(f"Écouteur Serveur: {nom_joueur} désenregistré de la map.")

    def _nettoyer_clients(self) -> None:
        """
        Supprime les threads GestionnaireClient qui ont terminé leur exécution.
        """
        # Utilise une compréhension de liste pour filtrer les threads actifs
        clients_avant = len(self.clients_actifs)
        self.clients_actifs = [c for c in self.clients_actifs if c.is_alive()]
        clients_apres = len(self.clients_actifs)

        if clients_avant > clients_apres:
            print(f"TCP Écouteur Serveur: {clients_avant - clients_apres} client(s) déconnecté(s) ou terminé(s).")

    def stop(self) -> None:
        """
        Arrête proprement l'écouteur en fermant le socket et en arrêtant tous les clients actifs.
        """
        print("TCP Écouteur Serveur: Arrêt demandé.")
        self.actif = False

        # Arrêter tous les gestionnaires de clients
        for client in self.clients_actifs:
            client.stop()

        # Fermer le socket principal pour débloquer self.socket_tcp.accept()
        if self.socket_tcp:
            # Créer un socket temporaire pour se connecter à soi-même et débloquer 'accept'
            # C'est une technique courante pour débloquer un appel bloquant
            try:
                temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                temp_socket.connect(('127.0.0.1', self.port))
                temp_socket.close()
            except Exception as e:
                # L'erreur est attendue si le socket est déjà en cours de fermeture
                print(e)

            self.socket_tcp.close()

        # Attendre la fin du thread lui-même
        if threading.get_ident() != self.ident:  # Évite le deadlock si stop() est appelé depuis le même thread
            self.join()