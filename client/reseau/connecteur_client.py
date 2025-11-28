import socket
import threading
import time
from typing import Tuple, Callable, Any

from commun import constantes as const
from commun.reseau.protocole import Protocole
from commun.reseau.message import Message


class ConnecteurClient:
    """
    Gère la double connexion (UDP pour l'authentification, TCP pour le jeu)
    et la communication réseau client-serveur.
    """

    def __init__(self, host_serveur: str, port_auth: int = const.PORT_AUTH, port_jeu: int = const.PORT_JEU):
        self.host_serveur = host_serveur
        self.port_auth = port_auth
        self.port_jeu = port_jeu

        self.socket_udp: socket.socket | None = None
        self.socket_tcp: socket.socket | None = None
        self.tcp_connecte = False
        self.nom_joueur: str | None = None

        # Callback pour passer les messages reçus à l'InterfaceConsole
        self.callback_traiter_message: Callable[[Message], None] | None = None

        self.thread_reception: threading.Thread | None = None
        self.actif = False

    def set_callback_traitement(self, callback: Callable[[Message], None]):
        """ Définit la fonction de l'interface qui traitera les messages reçus. """
        self.callback_traiter_message = callback

    # --- Phase 1: Authentification UDP ---

    def authentification_udp(self, nom: str, mdp: str, mode: str = const.MSG_AUTH_LOGIN) \
            -> tuple[bool, str, str | None, int | None, str | None]:
        """
        Tente de s'authentifier/s'inscrire via UDP.

        Returns:
            (succès, message, host_tcp, port_tcp, statut_partie)
        """
        self.socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_udp.settimeout(5)  # Attente maximale de 5 secondes

        # Création du message UDP simple (format attendu par AuthentificationUDP: TYPE|NOM|MDP)
        if mode == const.MSG_AUTH_LOGIN:
            message_obj = Message.creer_auth_login(nom, mdp)
        elif mode == const.MSG_AUTH_REGISTER:
            message_obj = Message.creer_auth_register(nom, mdp)
        else:
            return False, "Mode d'authentification inconnu.", None, None, None

        message_str = const.SEPARATEUR.join([message_obj.type, nom, mdp])

        try:
            # Envoi vers le serveur d'authentification (AuthentificationUDP)
            self.socket_udp.sendto(message_str.encode(const.ENCODAGE), (self.host_serveur, self.port_auth))

            # Réception de la réponse du serveur d'authentification UDP
            data, _ = self.socket_udp.recvfrom(1024)
            reponse_str = data.decode(const.ENCODAGE)
            parties = reponse_str.split(const.SEPARATEUR)

            status = parties[0]
            message = parties[1]

            if status == const.MSG_AUTH_SUCCESS:
                self.nom_joueur = nom
                host_tcp = parties[2]
                port_tcp = int(parties[3])

                # Vérifie si une partie sauvegardée existe (si l'information est présente)
                statut_partie = parties[4] if len(parties) > 4 else const.MSG_NOUVELLE_PARTIE

                return True, message, host_tcp, port_tcp, statut_partie
            else:
                return False, message, None, None, None

        except socket.timeout:
            return False, "Délai d'attente dépassé (Serveur UDP non joignable).", None, None, None
        except Exception as e:
            return False, f"Erreur de communication UDP: {e}", None, None, None
        finally:
            self.socket_udp.close()

    # --- Phase 2: Connexion TCP et Échange de Messages ---

    def connecter_tcp(self, host_tcp: str, port_tcp: int) -> bool:
        """ Établit la connexion TCP pour le jeu et commence la session. """
        try:
            self.socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_tcp.connect((host_tcp, port_tcp))
            self.tcp_connecte = True

            # Étape 1 TCP: Envoyer le MSG_CONNEXION à EcouteurServeur
            msg_connexion = Message.creer_connexion(self.nom_joueur)
            if Protocole.envoyer_message(self.socket_tcp, msg_connexion, const.CLIENT):
                self.demarrer_ecoute()  # Lancer le thread de réception immédiatement
                return True
            return False

        except Exception as e:
            print(f"Échec de la connexion TCP: {e}")
            self.tcp_connecte = False
            return False

    def envoyer_commande(self, message: Message) -> bool:
        """ Wrapper pour envoyer des commandes au serveur. """
        if not self.tcp_connecte or not self.socket_tcp:
            print("Erreur: Non connecté au serveur TCP.")
            return False

        return Protocole.envoyer_message(self.socket_tcp, message, const.CLIENT)

    def demarrer_ecoute(self):
        """ Démarre le thread d'écoute des messages TCP entrants. """
        if self.thread_reception is None or not self.thread_reception.is_alive():
            self.actif = True
            self.thread_reception = threading.Thread(target=self._boucle_reception, daemon=True)
            self.thread_reception.start()
            print("Thread de réception démarré dans ConnecteurClient.")

    def _boucle_reception(self):
        """ Boucle principale du thread pour recevoir les messages du serveur. """
        while self.actif:
            try:
                # Utiliser le protocole pour recevoir le message entier
                data = Protocole.recevoir_message(self.socket_tcp, const.CLIENT)

                if data is None:
                    # Serveur déconnecté ou erreur de Protocole
                    print("Déconnexion du serveur.")
                    break

                message = Message.deserialiser(data)

                if self.callback_traiter_message:
                    # Voir dans InterfaceConsole quelle est la Callback qui traite les messages reçus.
                    self.callback_traiter_message(message)
                else:
                    print(f"Message reçu (non traité): {message}")

            except Exception as e:
                if self.actif:
                    print(f"Erreur de réception TCP: {e}")
                break

        self.deconnecter()

    def deconnecter(self):
        """ Déconnecte proprement le client TCP. """
        self.actif = False
        self.tcp_connecte = False
        if self.socket_tcp:
            try:
                self.socket_tcp.close()
            except Exception:
                pass
        print("Client déconnecté.")