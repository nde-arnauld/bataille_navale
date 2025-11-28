import socket
import threading

from commun import constantes as const
from serveur.donnees.gestionnaire_utilisateur import GestionnaireUtilisateur


class AuthentificationUDP(threading.Thread):
    """
    Gère l'écoute UDP pour les requêtes d'authentification (login et inscription).
    """

    def __init__(self, gestionnaire_utilisateurs: GestionnaireUtilisateur, host: str = const.SERVEUR,
                 port: int = const.PORT_AUTH):
        super().__init__()
        self.host = host if host != const.SERVEUR else '0.0.0.0'  # Écoute sur toutes les interfaces
        self.port = port
        self.gestionnaire_utilisateurs = gestionnaire_utilisateurs
        self.socket_udp: socket.socket|None = None
        self.actif = True

    def run(self):
        """ Boucle principale du thread d'écoute UDP. """
        try:
            # Création du socket UDP (SOCK_DGRAM)
            self.socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket_udp.bind((self.host, self.port))
            print(f"UDP Auth: Écoute sur {self.host}:{self.port}")

            while self.actif:
                try:
                    # Taille du buffer pour recevoir les données
                    data, adresse_client = self.socket_udp.recvfrom(1024)

                    # Traiter la requête dans un thread pour ne pas bloquer la boucle
                    t = threading.Thread(target=self._traiter_requete, args=(data, adresse_client))
                    t.daemon = True # S'arrête automatiquement avec le thread principal
                    t.start()

                except socket.timeout as time_out:
                    print(f"UDP Auth Time out : {time_out}")
                    continue
                except Exception as e:
                    if self.actif:
                        print(f"UDP Auth Erreur de réception: {e}")

        except Exception as e:
            print(f"UDP Auth Échec de la liaison du socket: {e}")
        finally:
            if self.socket_udp:
                self.socket_udp.close()
            print("UDP Auth: Arrêté.")

    def _traiter_requete(self, data: bytes, adresse_client: tuple[str, int]):
        """
        Analyse la donnée UDP et appelle la logique d'authentification.
        Le format attendu du message est simple : TYPE_MESSAGE|NOM|MDP
        """
        try:
            message_str = data.decode(const.ENCODAGE)
            parties = message_str.split(const.SEPARATEUR)

            if len(parties) < 3:
                self._repondre_auth(const.MSG_AUTH_FAILED, adresse_client, "Format de requête invalide.")
                return

            type_msg, nom_joueur, mdp = parties[0], parties[1], parties[2]

            success = False

            if type_msg == const.MSG_AUTH_LOGIN:
                print(f"UDP Auth: Tentative de connexion pour: {nom_joueur}")
                success = self.gestionnaire_utilisateurs.verifier_authentification(nom_joueur, mdp)
                message = "Authentification réussie" if success else "Nom d'utilisateur ou mot de passe incorrect."

            elif type_msg == const.MSG_AUTH_REGISTER:
                print(f"UDP Auth: Tentative d'inscription pour: {nom_joueur}")
                success = self.gestionnaire_utilisateurs.enregistrer_utilisateur(nom_joueur, mdp)
                message = "Inscription réussie. Vous pouvez vous connecter." if success else "Nom déjà pris ou mot de passe trop court."

            else:
                message = "Type de message inconnu."

            self._repondre_auth(const.MSG_AUTH_SUCCESS if success else const.MSG_AUTH_FAILED, adresse_client, message,
                                nom_joueur)

        except Exception as e:
            print(f"UDP Auth Erreur de traitement de requête: {e}")
            self._repondre_auth(const.MSG_AUTH_FAILED, adresse_client, "Erreur interne du serveur.")

    def _repondre_auth(self, status: str, adresse_client: tuple[str, int], message: str, nom_joueur: str = ""):
        """
        Envoie la réponse d'authentification au client via UDP.
        Le message de succès inclut l'adresse TCP pour la phase de jeu.
        Format de réponse : STATUS|MESSAGE_TEXT|HOST_TCP|PORT_TCP
        """
        reponse = [status, message]

        if status == const.MSG_AUTH_SUCCESS:
            # Ajoute les informations de connexion TCP
            reponse.append(socket.gethostbyname(socket.gethostname()))  # IP locale du serveur
            reponse.append(str(const.PORT_JEU))

            # Vérifie s'il existe une partie sauvegardée pour ce joueur
            if self.gestionnaire_utilisateurs.partie_existe(nom_joueur):
                reponse.append(const.MSG_PARTIE_SAUVEGARDEE_EXISTE)
            else:
                reponse.append(const.MSG_NOUVELLE_PARTIE)

        reponse_str = const.SEPARATEUR.join(reponse)

        try:
            # Envoie la réponse à ConnecteurClient
            self.socket_udp.sendto(reponse_str.encode(const.ENCODAGE), adresse_client)
            print(f"UDP Auth: Réponse envoyée à {adresse_client[0]}:{adresse_client[1]} avec statut {status}")
        except Exception as e:
            print(f"UDP Auth Erreur d'envoi de réponse: {e}")

    def stop(self):
        """ Arrête la boucle du thread et ferme le socket. """
        self.actif = False
        if self.socket_udp:
            self.socket_udp.close()