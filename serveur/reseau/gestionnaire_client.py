import logging
import socket
import threading
import time
from typing import Any

from commun import constantes as const
from commun.coeur_jeu.joueur import Joueur
from commun.coeur_jeu.partie import Partie
from commun.reseau.message import Message
from commun.reseau.protocole import Protocole
from serveur.donnees.gestionnaire_utilisateur import GestionnaireUtilisateur
from serveur.logique_jeu.gestionnaire_partie import GestionnairePartie


class GestionnaireClient(threading.Thread):
    """
    Gère la session TCP et la logique de jeu pour un client unique.
    """

    def __init__(self, socket_client: socket.socket, adresse: tuple[str, int],
                 gestionnaire_utilisateurs: GestionnaireUtilisateur, gestionnaire_partie: GestionnairePartie) -> None:
        super().__init__()
        self.socket_client = socket_client
        self.adresse = adresse
        self.gestionnaire_utilisateurs = gestionnaire_utilisateurs
        self.actif = True
        self.nom_joueur: str | None = None
        self.partie_en_cours: Partie | None = None
        self.joueur_local: Joueur | None = None
        self.est_en_attente_pvp = False
        self.gestionnaire_partie = gestionnaire_partie
        self.mode_jeu: str | None = None
        self.callback_enregistrer = None
        self.callback_desenregistrer = None
        # Ajout du callback pour obtenir la map des clients (PvP)
        self.callback_get_map = None

    def set_callbacks(self, func_enregistrer, func_desenregistrer, func_get_map=None):
        """ Définit les fonctions pour s'enregistrer/désenregistrer et obtenir la map. """
        self.callback_enregistrer = func_enregistrer
        self.callback_desenregistrer = func_desenregistrer
        self.callback_get_map = func_get_map

    def run(self):
        """ Boucle principale de gestion du client. """
        print(f"[{self.adresse}] Démarrage du gestionnaire.")
        try:
            # 1. Établissement de la session et choix du type de partie (reprise ou nouvelle)
            if not self._initialiser_session():
                return

            # 2. Boucle de communication principale (Jeu/Chat/Déconnexion)
            self._boucle_communication()

        except ConnectionResetError:
            print(f"[{self.nom_joueur}] Déconnexion inattendue.")
        except Exception as e:
            nom = self.nom_joueur if self.nom_joueur else str(self.adresse)
            print(f"[{nom}] Erreur critique: {e}")
        finally:
            self.stop()

    def _initialiser_session(self) -> bool:
        """
        Gère la première séquence d'échanges TCP :
        1. Réception du nom d'utilisateur (confirmé par UDP).
        2. Choix de reprendre une partie ou d'en lancer une nouvelle.
        """
        # 1. Réception du nom d'utilisateur
        data = Protocole.recevoir_message(self.socket_client, const.SERVEUR)
        if not data: return False

        msg_connexion = Message.deserialiser(data)
        if msg_connexion.type != const.MSG_CONNEXION:
            return False

        self.nom_joueur = msg_connexion.donnees.get("nom", "Inconnu")
        print(f"[{self.nom_joueur}] Connexion TCP établie.")

        # La callback_enregistrer() est paramétrée dans EcouteurServeur
        if self.callback_enregistrer and self.nom_joueur:
            self.callback_enregistrer(self.nom_joueur, self)

        # 2. Vérification de la sauvegarde
        if self.gestionnaire_utilisateurs.partie_existe(self.nom_joueur):
            msg_ok = Message.creer_connexion_ok(f"Bienvenue {self.nom_joueur}! Partie sauvegardée trouvée.")
            msg_ok.donnees["reprise"] = True  # Indicateur de reprise
            Protocole.envoyer_message(self.socket_client, msg_ok, const.SERVEUR)

            # Attendre la décision du client (Reprendre/Nouvelle)
            return self._gerer_choix_reprise()

        else:
            msg_ok = Message.creer_connexion_ok(f"Bienvenue {self.nom_joueur}!")
            Protocole.envoyer_message(self.socket_client, msg_ok, const.SERVEUR)
            return True  # Continuer vers le choix de mode

    def _gerer_choix_reprise(self) -> bool:
        """ Attends et traite le choix du client concernant la partie sauvegardée. """
        data = Protocole.recevoir_message(self.socket_client, const.SERVEUR)
        if not data: return False

        msg_choix = Message.deserialiser(data)

        if msg_choix.type == const.MSG_REPRENDRE_PARTIE:
            # Tente de charger la partie
            partie = self.gestionnaire_utilisateurs.charger_partie(self.nom_joueur)

            if partie:
                partie.etat = const.ETAT_EN_COURS
                self.partie_en_cours = partie
                # On doit déterminer quel joueur est ce client dans l'objet Partie
                self.joueur_local = partie.joueur1 if partie.joueur1.nom == self.nom_joueur else partie.joueur2

                # On récupère le nom de l'adversaire
                nom_adversaire = partie.joueur2.nom if partie.joueur1.nom == self.nom_joueur else partie.joueur1.nom

                est_tour_joueur1 = partie.est_tour_joueur1
                est_mon_tour = (est_tour_joueur1 and self.joueur_local.nom == partie.joueur1.nom) or \
                               (not est_tour_joueur1 and self.joueur_local.nom == partie.joueur2.nom)

                # PRÉPARATION DES DONNÉES DE REPRISE
                joueur_data = self.joueur_local.to_dict()
                msg_reprise_data = {
                    "joueur_etat": joueur_data,
                    "est_mon_tour": est_mon_tour,
                    "nom_adversaire": nom_adversaire
                }

                msg_reprise = Message.creer_message_reprise(msg_reprise_data)

                # Si l'IA est identifiée:
                if nom_adversaire == const.NOM_SERVEUR:

                    # --- MODE SOLO (Reprise immédiate) ---
                    self.mode_jeu = const.MODE_VS_SERVEUR
                    Protocole.envoyer_message(self.socket_client, msg_reprise, const.SERVEUR)

                    # L'IA étant déjà dans la partie, le GestionnaireClient passera directement
                    # à la boucle de jeu principale et recevra le tour suivant du serveur.
                    print(f"[{self.nom_joueur}] Partie Solo sauvegardée chargée.")
                    return True

                else:
                    # --- MODE PvP (Attente de l'adversaire) ---
                    self.mode_jeu = const.MODE_VS_JOUEUR

                    # Le GestionnaireClient doit s'enregistrer auprès du GestionnairePartie
                    # pour retrouver son adversaire ou attendre qu'il se connecte.

                    # 1. Notifier le client qu'il doit attendre
                    self.est_en_attente_pvp = True
                    self.gestionnaire_partie.mettre_en_attente(self)  # Le client est mis en file d'attente/recherche

                    # 2. Envoyer le message de confirmation (le client passera en état d'attente)
                    Protocole.envoyer_message(self.socket_client, msg_reprise, const.SERVEUR)
                    print(f"[{self.nom_joueur}] Partie PvP chargée. Mis en attente de {nom_adversaire}.")
                    return True

            else:
                # Échec du chargement (ne devrait pas arriver si partie_existe a dit oui)
                Protocole.envoyer_message(self.socket_client, Message(const.MSG_ERREUR, {"detail": "Échec chargement"}), const.SERVEUR)
                return False

        elif msg_choix.type == const.MSG_NOUVELLE_PARTIE:
            # Supprimer l'ancienne sauvegarde
            self.gestionnaire_utilisateurs.supprimer_partie_sauvegardee(self.nom_joueur)
            Protocole.envoyer_message(self.socket_client, Message.creer_connexion_ok("Nouvelle partie démarrée."), const.SERVEUR)
            time.sleep(0.1) # un peu d'attente
            Protocole.envoyer_message(self.socket_client, Message(const.MSG_NOUVELLE_PARTIE), const.SERVEUR)
            return True

        return False

    def _envoyer_message_tcp(self, message: Message) -> bool:
        """ Wrapper autour de Protocole.envoyer_message. """
        return Protocole.envoyer_message(self.socket_client, message, const.SERVEUR)

    def _boucle_communication(self):
        """ Boucle principale de réception des commandes de jeu et de chat. """
        while self.actif:
            data = Protocole.recevoir_message(self.socket_client, const.SERVEUR)
            if not data:
                break  # Déconnexion ou erreur

            message = Message.deserialiser(data)

            if message.type == const.MSG_TIR:
                self._traiter_tir_client(message.donnees["x"], message.donnees["y"])

            elif message.type == const.MSG_PLACEMENT_NAVIRES:
                self._gerer_placement_navires(message)

            elif message.type == const.MSG_CHAT:
                self._transmettre_chat(message.donnees["message"])

            elif message.type == const.MSG_DECONNEXION or message.type == const.MSG_ABANDON or message.type == const.MSG_SAUVEGARDER_PARTIE:
                self._traiter_deconnexion_sauvegarde(message.type)
                break

            elif message.type == const.MSG_CHOIX_MODE:
                self._gerer_choix_mode(message.donnees["mode"])

    def _gerer_choix_mode(self, mode: str) -> None:
        """ Gère le choix du mode de jeu (Solo ou PvP). """

        self.mode_jeu = mode

        if mode == const.MODE_VS_SERVEUR:
            # Création du Joueur local et initialisation de la Partie Solo
            self.joueur_local = Joueur(self.nom_joueur)

            # On suppose que Partie(joueur) crée une partie Solo avec une IA en tant que joueur 2.
            self.partie_en_cours = Partie(self.joueur_local)
            self.partie_en_cours.initialiser_joueur_ia()  # Appel supposé pour créer l'IA (Joueur 2)

            # Notifier le client que la partie est prête (le client doit maintenant placer)
            self._envoyer_message_tcp(Message(const.MSG_DEBUT_PARTIE))
            print(f"[{self.nom_joueur}] Envoi de MSG_DEBUT_PARTIE, attente du placement.")

        elif mode == const.MODE_VS_JOUEUR:
            # Logique PvP
            self.est_en_attente_pvp = True
            self.gestionnaire_partie.mettre_en_attente(self)
            self._envoyer_message_tcp(Message(const.MSG_ATTENTE_ADVERSAIRE))


    def _gerer_placement_navires(self, message: Message):
        """ Gère la réception des positions des navires du client et lance le jeu Solo. """
        positions: list[dict[str, Any]] = message.donnees.get("navires", [])

        if not self.partie_en_cours or not self.joueur_local:
            self._envoyer_message_tcp(Message.creer_erreur("Partie non initialisée pour le placement."))
            return

        try:
            # 1. Placement des navires du joueur (client)
            self.joueur_local.placer_navires_depuis_positions(positions)

            if self.mode_jeu == const.MODE_VS_SERVEUR:
                # 2. Placement des navires de l'IA (Joueur 2)
                joueur_ia = self.partie_en_cours.joueur2
                if joueur_ia:
                    joueur_ia.placer_navires_aleatoire()

                # 3. Démarrer la partie
                self.partie_en_cours.demarrer()

                # 4. Confirmation au client
                self._envoyer_message_tcp(Message(const.MSG_PLACEMENT_OK))
                print(f"[GestionnaireClient: {self.nom_joueur}] Placement validé, partie Solo lancée.")

                # 5. Lancer le premier tour
                self._lancer_tour_initial()
            elif self.mode_jeu == const.MODE_VS_JOUEUR:
                # --- MODE PvP (Logique déléguée) ---

                # La Partie n'est PAS démarrée ici, car elle est en attente de l'adversaire.
                #
                # On stocke l'état du placement local du client (déjà fait par placer_navires_depuis_positions)
                # et on notifie le GestionnairePartie que ce client est PRÊT.

                self._envoyer_message_tcp(Message(const.MSG_PLACEMENT_OK))
                print(f"[{self.nom_joueur}] Placement PvP validé. En attente de l'adversaire...")

                # Notifier le GestionnairePartie que le client est prêt
                self.gestionnaire_partie.notifier_client_pret(self, self.callback_get_map())

            else:
                # Mode non géré ou indéfini (Erreur)
                self._envoyer_message_tcp(Message.creer_erreur("Mode de jeu non spécifié."))

        except Exception as e:
            # Si le placement échoue (coordonnées invalides, etc.)
            logging.exception(f"[{self.nom_joueur}] Erreur de placement: {e}]")
            self._envoyer_message_tcp(Message.creer_erreur(f"Erreur de placement: {e}. Réessayez."))

    # Logique de début de tour
    def _lancer_tour_initial(self):
        """ Détermine le premier tour et notifie le client. """
        # La partie en cours doit avoir une logique pour déterminer qui commence
        if self.partie_en_cours.est_tour_joueur1:  # joueur1 est le client
            self.notifier_tour(True)  # C'est le tour du client
        else:
            self.notifier_tour(False)  # C'est le tour de l'IA
            # Si c'est le tour de l'IA, on exécute son action immédiatement
            self._executer_tour_ia()

    def _executer_tour_ia(self):
        """ Exécute le tour de l'IA (Solo). """
        print(f"[{self.nom_joueur}] Tour de l'IA en cours...")

        if not self.partie_en_cours:
            print(f"[{self.nom_joueur}] Erreur: Partie non active pour l'IA.")
            return

        joueur_ia = self.partie_en_cours.joueur2

        # 1. L'IA choisit ses coordonnées
        x_tir, y_tir = GestionnaireClient.choisir_tir_aleatoire(joueur_ia)

        # 2. La Partie traite le tir (la méthode traiter_tir fait l'action et change de tour interne).
        resultat, navire_coule, partie_terminee = self.partie_en_cours.traiter_tir(x_tir, y_tir)

        print(f"[{self.nom_joueur}] L'IA a tiré en ({x_tir}, {y_tir}). Résultat: {resultat}.")

        # 3. Notifier le client du coup REÇU
        # On utilise notifier_tir_recu pour signaler au client l'attaque sur sa propre grille
        self.notifier_tir_recu(x_tir, y_tir, resultat, joueur_ia.nom, navire_coule)

        if partie_terminee:
            # L'IA a gagné!
            self._envoyer_message_tcp(Message.creer_fin_partie(joueur_ia.nom, " vous a coulé!"))
            self.stop()
            return

        # 5. Renvoyer le tour au client
        # Le tour a déjà changé dans self.partie_en_cours.traiter_tir(),
        # donc on notifie le joueur que c'est maintenant SON tour (True).
        self.notifier_tour(True)
        print(f"[{self.nom_joueur}] Tour de l'IA terminé. Votre tour.")

    @staticmethod
    def choisir_tir_aleatoire(joueur: Joueur):
        """Choisit un tir aléatoire non encore effectué"""
        import random

        for _ in range(1000):
            x = random.randint(0, const.TAILLE_GRILLE - 1)
            y = random.randint(0, const.TAILLE_GRILLE - 1)

            case = joueur.grille_suivi[y][x]
            if case == const.CASE_EAU or case == const.CASE_NAVIRE:
                return x, y

        return 0, 0

    def notifier_erreur(self, texte: str):
        msg_erreur = Message.creer_erreur(texte)
        self._envoyer_message_tcp(msg_erreur)

    def notifier_debut_partie(self, nom_adversaire: str, mode: str):
        msg_erreur = Message.creer_debut_partie(nom_adversaire, mode)
        self._envoyer_message_tcp(msg_erreur)

    def notifier_match_trouve(self, nom_adversaire: str):
        """ Notifie le client qu'un match a été trouvé. """
        msg_adv = Message.creer_adversaire_trouve(nom_adversaire)
        self._envoyer_message_tcp(msg_adv)

    def notifier_tir_recu(self, x: int, y: int, resultat: str, tireur: str, navire_coule: str | None):
        """ Notifie le client qu'il a reçu un tir. """
        msg = Message.creer_reponse_tir_recu(resultat, x, y, tireur, navire_coule)
        self._envoyer_message_tcp(msg)

    def notifier_resultat_tir(self, x: int, y: int, resultat: str, navire_coule: str | None):
        """ Notifie le client du résultat de son propre tir. """
        msg = Message.creer_reponse_tir(resultat, x, y, navire_coule)
        self._envoyer_message_tcp(msg)

    def notifier_fin_partie(self, status: str, message: str):
        msg = Message(const.MSG_FIN_PARTIE, {"status": status, "message": message})
        self._envoyer_message_tcp(msg)

    def notifier_tour(self, est_son_tour: bool):
        """ Notifie le client si c'est son tour ou celui de l'adversaire. """
        if est_son_tour:
            self._envoyer_message_tcp(Message.creer_votre_tour())
        else:
            self._envoyer_message_tcp(Message.creer_tour_adversaire())

    def envoyer_chat(self, nom_envoyeur: str, message: str):
        """ Envoie un message de chat reçu d'un autre client. """
        msg = Message(const.MSG_CHAT_GLOBAL, {"envoyeur": nom_envoyeur, "message": message})
        self._envoyer_message_tcp(msg)

    # --- Méthodes de traitement des commandes ---

    def _traiter_tir_client(self, x: int, y: int) -> None:
        """ Gère une commande de tir du client, en déléguant selon le mode de jeu. """

        if not self.partie_en_cours or self.mode_jeu is None:
            print(f"[GESTIONNAIRE CLIENT (traiter_tir_client)]: "
                  f"ERREUR (partie_en_cours: {self.partie_en_cours}, mode_jeu: {self.mode_jeu}, est_tour_joueur1: {self.partie_en_cours.est_tour_joueur1})")
            # Non, ce n'est pas le tour (ou la partie n'est pas initialisée).
            self._envoyer_message_tcp(Message(const.MSG_ERREUR, {"detail": "Ce n'est pas votre tour ou partie non démarrée."}))
            return

        # Si nous sommes ici, c'est le tour du joueur et la partie est en cours.

        if self.mode_jeu == const.MODE_VS_SERVEUR:
            # LOGIQUE SOLO : Gérée par le thread local du client

            # Note: Si votre Partie.traiter_tir ne gère pas de 'partie_terminee', il faudra l'ajouter.
            resultat, navire_coule, partie_terminee = self.partie_en_cours.traiter_tir(x, y)

            self.notifier_resultat_tir(x, y, resultat, navire_coule)

            if partie_terminee:
                self._envoyer_message_tcp(Message.creer_fin_partie(self.nom_joueur, " Félicitations vous avez gagné!"))
                # self.stop()
                return

            self._executer_tour_ia()

        elif self.mode_jeu == const.MODE_VS_JOUEUR:
            # LOGIQUE PvP : Délégation au GestionnairePartie

            if self.callback_get_map is None:
                self._envoyer_message_tcp(Message.creer_erreur("Erreur serveur interne (map non fournie)."))
                return

            clients_actifs_map = self.callback_get_map()

            # Délégation de la tâche à la logique centrale (GestionnairePartie)
            self.gestionnaire_partie.traiter_tir(
                tireur_client=self,
                clients_actifs_map=clients_actifs_map,
                x=x,
                y=y
            )

        else:
            self._envoyer_message_tcp(Message.creer_erreur("Mode de jeu inconnu."))

    def _transmettre_chat(self, message: str) -> None:
        """ Envoie le message de chat à l'adversaire (via GestionnairePartie) ou le journal local. """
        print(f"[CHAT {self.nom_joueur}] {message}")
        clients_actifs_map = self.callback_get_map()
        self.gestionnaire_partie.transmettre_chat(
            envoyeur_client=self,
            message=message,
            clients_actifs_map=clients_actifs_map,
        )

    def _traiter_deconnexion_sauvegarde(self, type_message: str) -> None:
        """ Gère la déconnexion, l'abandon ou la sauvegarde. """
        if type_message == const.MSG_SAUVEGARDER_PARTIE:
            if self.partie_en_cours:
                # Le joueur local est j1 ou j2 dans la partie en cours.
                self.gestionnaire_utilisateurs.sauvegarder_partie(self.nom_joueur, self.partie_en_cours)
                print(f"[{self.nom_joueur}] Partie sauvegardée avec succès.")

        elif type_message == const.MSG_ABANDON and self.partie_en_cours:
            self.partie_en_cours.abandonner(self.nom_joueur)
            self.gestionnaire_utilisateurs.supprimer_partie_sauvegardee(self.nom_joueur)
            # Logique PvP: Notifier l'adversaire via GESTIONNAIRE_PARTIE

        print(f"[{self.nom_joueur}] Déconnexion demandée.")
        self.actif = False  # Sortie de boucle

    def stop(self):
        """ Arrête le thread et ferme le socket client. """
        self.actif = False
        if self.socket_client:
            try:
                if self.callback_desenregistrer and self.nom_joueur:
                    self.callback_desenregistrer(self.nom_joueur)
                self.socket_client.close()
            except Exception as e:
                print(f"[{self.nom_joueur}] Erreur à la fermeture du socket: {e}")
        print(f"[{self.nom_joueur}] Thread terminé.")