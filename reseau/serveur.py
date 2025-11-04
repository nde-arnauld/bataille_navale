import socket
import threading
import random
from .protocole import Protocole
from .message import Message
from base import Joueur, Partie

class Serveur:
    def __init__(self, host='0.0.0.0', port=5555):
        """
        Initialise le serveur

        Args:
            host: Adresse d'écoute
            port: Port d'écoute
        """
        self.host = host
        self.port = port
        self.socket_serveur = None
        self.actif = False
        self.clients_en_attente = []  # Liste des clients en attente d'adversaire
        self.lock_attente = threading.Lock()  # Pour synchroniser l'accès

    def demarrer(self):
        """Démarre le serveur"""
        try:
            # Créer le socket serveur
            self.socket_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket_serveur.bind((self.host, self.port))
            self.socket_serveur.listen(5)

            self.actif = True
            print(f"[SERVEUR] Démarré sur {self.host}:{self.port}")
            print(f"[SERVEUR] En attente de connexions...")

            # Boucle d'acceptation des connexions
            while self.actif:
                try:
                    client_socket, adresse = self.socket_serveur.accept()
                    print(f"[SERVEUR] Nouvelle connexion de {adresse}")

                    # Créer un thread pour gérer ce client
                    thread_client = threading.Thread(
                        target=self.gerer_client,
                        args=(client_socket, adresse)
                    )
                    thread_client.daemon = True
                    thread_client.start()

                except Exception as e:
                    if self.actif:
                        print(f"[SERVEUR] Erreur d'acceptation: {e}")

        except Exception as e:
            print(f"[SERVEUR] Erreur de démarrage: {e}")
        finally:
            self.arreter()

    def gerer_client(self, client_socket, adresse):
        """
        Gère la communication avec un client (exécuté dans un thread)

        Args:
            client_socket: Socket du client
            adresse: Adresse du client
        """
        nom_client = None
        fermer_socket = True  # Par défaut, on ferme le socket à la fin

        try:
            # ========== ÉTAPE 1: CONNEXION ==========
            data = self.recevoir_message(client_socket)
            if not data:
                print(f"[CLIENT {adresse}] Connexion échouée")
                return

            msg_connexion = Message.deserialiser(data)
            if msg_connexion.type != Protocole.MSG_CONNEXION:
                print(f"[CLIENT {adresse}] Message de connexion attendu, reçu: {msg_connexion.type}")
                return

            nom_client = msg_connexion.donnees.get("nom", "Joueur")
            print(f"[CLIENT {adresse}] Connexion de '{nom_client}'")

            # Envoyer la confirmation de connexion
            msg_ok = Message.creer_connexion_ok(f"Bienvenue {nom_client}!")
            self.envoyer_message(client_socket, msg_ok)

            # ========== ÉTAPE 2: CHOIX DU MODE ==========
            data = self.recevoir_message(client_socket)
            if not data:
                return

            msg_mode = Message.deserialiser(data)
            if msg_mode.type != Protocole.MSG_CHOIX_MODE:
                print(f"[CLIENT {adresse}] Message de choix du mode attendu, reçu: {msg_mode.type}")
                return

            mode = msg_mode.donnees.get("mode")
            print(f"[CLIENT {adresse}] Mode choisi: {mode}")

            if mode == Protocole.MODE_VS_SERVEUR:
                self.mode_vs_serveur(client_socket, adresse, nom_client)
                # Mode VS Serveur termine normalement, on ferme le socket
                fermer_socket = True

            elif mode == Protocole.MODE_VS_JOUEUR:
                # Mode PvP peut retourner True (partie jouée) ou False (en attente)
                partie_jouee = self.mode_vs_joueur(client_socket, adresse, nom_client)

                if partie_jouee:
                    # La partie a été jouée, on peut fermer le socket
                    fermer_socket = True
                else:
                    # Client en attente, NE PAS fermer le socket.
                    # Il est dans la file d'attente, un autre thread s'en occupera
                    fermer_socket = False
                    print(f"[CLIENT {adresse}] Socket gardé ouvert pour matchmaking")

        except Exception as e:
            print(f"[CLIENT {adresse}] Erreur: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if fermer_socket:
                print(f"[CLIENT {adresse}] Déconnexion")
                try:
                    client_socket.close()
                except Exception as e:
                    print(f"[CLIENT {adresse}] Erreur: {e}")
            else:
                print(f"[CLIENT {adresse}] Thread terminé (socket reste ouvert)")

    def mode_vs_serveur(self, client_socket, adresse, nom_client):
        """Mode de jeu contre le serveur"""
        print(f"[CLIENT {adresse}] Mode VS Serveur")

        # Recevoir le placement des bateaux
        joueur_client = self.recevoir_placement_bateaux(client_socket, adresse, nom_client)
        if not joueur_client:
            print(f"[CLIENT {adresse}] Erreur de placement de bateaux")
            return

        # Créer le joueur serveur
        joueur_serveur = Joueur("Serveur")
        joueur_serveur.placer_bateaux_aleatoire()

        # Créer la partie
        partie = Partie(joueur_client, joueur_serveur)
        partie.etat = Protocole.ETAT_EN_COURS

        # Envoyer début de partie
        msg_debut = Message.creer_debut_partie()
        self.envoyer_message(client_socket, msg_debut)

        # Boucle de jeu
        self.boucle_jeu_vs_serveur(client_socket, partie, adresse)

    def mode_vs_joueur(self, client_socket: socket.socket, adresse, nom_client: str):
        """Mode de jeu contre un autre joueur"""
        print(f"[CLIENT {adresse}] Mode VS Joueur")

        # Recevoir le placement des bateaux
        joueur_client = self.recevoir_placement_bateaux(client_socket, adresse, nom_client)
        if not joueur_client:
            print(f"[CLIENT {adresse}] Erreur de placement de bateaux]")
            return None

        # Chercher un adversaire
        adversaire_info = self.trouver_adversaire(client_socket, adresse, nom_client, joueur_client)

        if not adversaire_info:
            print(f"[CLIENT {adresse}] Erreur, pas d'adversaire trouvé!")
            # Ce client est en attente
            print(f"[CLIENT {adresse}] Mis en attente - Thread va se terminer")
            print(f"[CLIENT {adresse}] MAIS le socket reste ouvert!")
            # Le thread se termine ici, mais le socket reste dans la file
            return None

        adversaire_socket, adversaire_nom, joueur_adversaire, est_joueur1 = adversaire_info

        print(f"[MATCH] {nom_client} VS {adversaire_nom}")
        print(f"[MATCH] Thread actuel gère les deux joueurs")

        # Créer la partie
        partie = Partie(joueur_client, joueur_adversaire)
        partie.etat = Protocole.ETAT_EN_COURS

        # Notifier les deux joueurs
        print(f"[MATCH] Envoi MSG_DEBUT_PARTIE aux deux joueurs...")
        msg_debut = Message.creer_debut_partie()
        self.envoyer_message(client_socket, msg_debut)
        self.envoyer_message(adversaire_socket, msg_debut)
        print(f"[MATCH] MSG_DEBUT_PARTIE envoyé")

        # Lancer la boucle de jeu
        self.boucle_jeu_pvp(
            client_socket, adversaire_socket,
            partie, nom_client, adversaire_nom
        )

        print(f"[MATCH] Partie terminée: {nom_client} VS {adversaire_nom}")
        return  True

    def recevoir_placement_bateaux(self, client_socket, adresse, nom_client):
        """Reçoit et valide le placement des bateaux"""
        data = self.recevoir_message(client_socket)
        if not data:
            return None

        msg_placement = Message.deserialiser(data)
        if msg_placement.type != Protocole.MSG_PLACEMENT_BATEAUX:
            return None

        positions = msg_placement.donnees.get("bateaux", [])
        joueur = Joueur(nom_client)

        if not joueur.placer_bateaux_depuis_positions(positions):
            msg_erreur = Message.creer_erreur("Placement invalide")
            self.envoyer_message(client_socket, msg_erreur)
            return None

        msg_ok = Message.creer_placement_ok()
        self.envoyer_message(client_socket, msg_ok)

        return joueur

    def boucle_jeu_vs_serveur(self, client_socket, partie, adresse):
        """Boucle de jeu contre le serveur"""

        while not partie.est_terminee():
            try:
                if partie.est_tour_joueur1():
                    # Tour du client
                    data = self.recevoir_message(client_socket)
                    if not data:
                        break

                    message = Message.deserialiser(data)

                    if message.type == Protocole.MSG_TIR:
                        x = message.donnees["x"]
                        y = message.donnees["y"]

                        resultat, bateau_coule, termine = partie.traiter_tir(x, y)

                        msg_reponse = Message.creer_reponse_tir(resultat, x, y, bateau_coule)
                        self.envoyer_message(client_socket, msg_reponse)

                        if termine:
                            msg_fin = Message.creer_fin_partie(partie.obtenir_gagnant(), "Partie terminée!")
                            self.envoyer_message(client_socket, msg_fin)
                            break

                    elif message.type == Protocole.MSG_ABANDON:
                        partie.abandonner(partie.joueur1.nom)
                        break

                else:
                    # Tour du serveur
                    x, y = self.choisir_tir_aleatoire(partie.joueur2)

                    resultat, bateau_coule, termine = partie.traiter_tir(x, y)

                    msg_tir = Message.creer_tir(x, y)
                    self.envoyer_message(client_socket, msg_tir)

                    msg_reponse = Message.creer_reponse_tir(resultat, x, y, bateau_coule)
                    self.envoyer_message(client_socket, msg_reponse)

                    if termine:
                        msg_fin = Message.creer_fin_partie(partie.obtenir_gagnant(), "Partie terminée!")
                        self.envoyer_message(client_socket, msg_fin)
                        break

            except Exception as e:
                print(f"[CLIENT {adresse}] Erreur: {e}")
                break

    def choisir_tir_aleatoire(self, joueur):
        """Choisit un tir aléatoire non encore effectué"""
        import random

        for _ in range(1000):
            x = random.randint(0, Protocole.TAILLE_GRILLE - 1)
            y = random.randint(0, Protocole.TAILLE_GRILLE - 1)

            if joueur.grille_suivi[y][x] == Protocole.CASE_EAU:
                return x, y

        return 0, 0

    def boucle_jeu_pvp(self, socket1: socket.socket, socket2: socket.socket, partie: Partie, nom1:str, nom2: str):
        """
        Boucle de jeu entre deux joueurs

        IMPORTANT: Cette méthode est exécutée par UN SEUL THREAD
        qui gère les deux sockets simultanément

        Args:
            socket1: Socket du joueur 1
            socket2: Socket du joueur 2
            partie: Instance de Partie partagée
            nom1: Nom du joueur 1
            nom2: Nom du joueur 2
        """
        print(f"[PVP] Début de la partie {nom1} VS {nom2}")
        print(f"Partie active : {partie}")

        while not partie.est_terminee():
            try:
                # Déterminer quel joueur doit jouer
                if partie.est_tour_joueur1():
                    socket_actif = socket1
                    socket_passif = socket2
                    nom_actif = nom1
                else:
                    socket_actif = socket2
                    socket_passif = socket1
                    nom_actif = nom2

                print(f"[PVP] Tour de {nom_actif}")

                # Notifier les deux joueurs
                msg_tour = Message.creer_votre_tour()
                self.envoyer_message(socket_actif, msg_tour)

                msg_attente = Message.creer_tour_adversaire()
                self.envoyer_message(socket_passif, msg_attente)

                # Recevoir le tir du joueur actif
                data = self.recevoir_message(socket_actif)
                if not data:
                    print(f"[PVP] {nom_actif} déconnecté")
                    break

                message = Message.deserialiser(data)

                if message.type == Protocole.MSG_TIR:
                    x = message.donnees["x"]
                    y = message.donnees["y"]

                    print(f"[PVP] {nom_actif} tire en ({x}, {y})")

                    # Traiter le tir sur la partie partagée
                    resultat, bateau_coule, termine = partie.traiter_tir(x, y)

                    print(f"[PVP] Résultat: {resultat}")

                    # Envoyer le résultat aux DEUX joueurs
                    msg_reponse = Message.creer_reponse_tir(resultat, x, y, bateau_coule)
                    self.envoyer_message(socket_actif, msg_reponse)
                    self.envoyer_message(socket_passif, msg_reponse)

                    # Vérifier si la partie est terminée
                    if termine:
                        gagnant = partie.obtenir_gagnant()
                        print(f"[PVP] Partie terminée! Gagnant: {gagnant}")

                        msg_fin = Message.creer_fin_partie(gagnant, "Partie terminée!")
                        self.envoyer_message(socket_actif, msg_fin)
                        self.envoyer_message(socket_passif, msg_fin)
                        break

                elif message.type == Protocole.MSG_ABANDON:
                    print(f"[PVP] {nom_actif} a abandonné")
                    gagnant = nom2 if nom_actif == nom1 else nom1

                    msg_fin = Message.creer_fin_partie(gagnant, f"{nom_actif} a abandonné")
                    self.envoyer_message(socket_actif, msg_fin)
                    self.envoyer_message(socket_passif, msg_fin)
                    break

            except Exception as e:
                print(f"[PVP] Erreur: {e}")
                import traceback
                traceback.print_exc()
                break

        print(f"[PVP] Fin de la partie {nom1} VS {nom2}")

    def trouver_adversaire(self, client_socket, adresse, nom_client, joueur_client):
        """
        Trouve un adversaire ou met en attente

        IMPORTANT: Cette méthode retourne None pour le premier joueur (mis en attente)
        et retourne les infos de l'adversaire pour le deuxième joueur
        """
        with self.lock_attente:
            if len(self.clients_en_attente) > 0:
                # Il y a quelqu'un en attente ! On fait un match
                adversaire_info = self.clients_en_attente.pop(0)
                adversaire_socket, adversaire_adresse, adversaire_nom, joueur_adversaire = adversaire_info

                print(f"[MATCHMAKING] {nom_client} VS {adversaire_nom}")

                # Notifier les deux joueurs qu'un adversaire a été trouvé
                msg_trouve_adv = Message.creer_adversaire_trouve(adversaire_nom)
                self.envoyer_message(client_socket, msg_trouve_adv)

                msg_trouve_client = Message.creer_adversaire_trouve(nom_client)
                self.envoyer_message(adversaire_socket, msg_trouve_client)

                # Retourner les infos de l'adversaire
                # Le thread ACTUEL va gérer la partie pour les deux joueurs
                return (adversaire_socket, adversaire_adresse, adversaire_nom, joueur_adversaire)
            else:
                # Personne en attente, on met ce client dans la file
                print(f"[CLIENT {adresse}] Mis en file d'attente...")
                msg_attente = Message.creer_attente_adversaire()
                self.envoyer_message(client_socket, msg_attente)

                # Ajouter à la file d'attente
                self.clients_en_attente.append((client_socket, adresse, nom_client, joueur_client))

                # Retourner None : ce thread s'arrête ici
                # Le client reste connecté, mais son thread initial se termine
                # Quand un adversaire arrive, l'AUTRE thread gérera la partie
                return None

    def trouver_adversaire_2(self, client_socket, adresse, nom_client, joueur_client):
        """Trouve un adversaire ou met en attente"""
        with self.lock_attente:
            if len(self.clients_en_attente) > 0:
                # Prendre le premier en attente
                adversaire_info = self.clients_en_attente.pop(0)
                adversaire_socket, adversaire_adresse, adversaire_nom, joueur_adversaire = adversaire_info

                print(f"[MATCHMAKING] {nom_client} VS {adversaire_nom}")

                # Notifier les deux joueurs
                msg_trouve = Message.creer_adversaire_trouve(adversaire_nom)
                self.envoyer_message(client_socket, msg_trouve)

                msg_trouve = Message.creer_adversaire_trouve(nom_client)
                self.envoyer_message(adversaire_socket, msg_trouve)

                return (adversaire_socket, adversaire_nom, joueur_adversaire, True)
            else:
                # Mettre en attente
                print(f"[CLIENT {adresse}] En attente d'adversaire...")
                msg_attente = Message.creer_attente_adversaire()
                self.envoyer_message(client_socket, msg_attente)

                self.clients_en_attente.append((client_socket, adresse, nom_client, joueur_client))
                return None

    def boucle_jeu(self, client_socket, partie, adresse):
        """
        Gère la boucle de jeu pour un client

        Args:
            client_socket: Socket du client
            partie: Instance de la partie
            adresse: Adresse du client
        """
        while not partie.est_terminee():
            try:
                # Attendre un message du client
                data = self.recevoir_message(client_socket)
                if not data:
                    print(f"[CLIENT {adresse}] Connexion perdue")
                    break

                message = Message.deserialiser(data)
                type_msg = message.obtenir_type()

                if type_msg == Protocole.MSG_TIR:
                    # Traiter le tir du client
                    x = message.obtenir_donnee("x")
                    y = message.obtenir_donnee("y")

                    print(f"[CLIENT {adresse}] Tir reçu en ({x}, {y})")

                    # Traiter le tir
                    resultat, bateau_coule, partie_terminee = partie.traiter_tir(x, y)

                    # Envoyer la réponse au client
                    msg_reponse = Message.creer_reponse_tir(resultat, x, y, bateau_coule)
                    self.envoyer_message(client_socket, msg_reponse)

                    print(f"[CLIENT {adresse}] Résultat: {resultat}")

                    # Vérifier si la partie est terminée
                    if partie_terminee:
                        msg_fin = Message.creer_fin_partie(
                            partie.obtenir_gagnant(),
                            f"Partie terminée! Gagnant: {partie.obtenir_gagnant()}"
                        )
                        self.envoyer_message(client_socket, msg_fin)
                        print(f"[CLIENT {adresse}] Partie terminée")
                        break

                    # Tour du serveur (si le client a raté)
                    if not partie.est_tour_joueur1():
                        self.jouer_tour_serveur(client_socket, partie, adresse)

                elif type_msg == Protocole.MSG_ABANDON:
                    print(f"[CLIENT {adresse}] Abandon de la partie")
                    partie.abandonner(partie.joueur1.nom)
                    msg_fin = Message.creer_fin_partie(
                        partie.obtenir_gagnant(),
                        "Partie abandonnée"
                    )
                    self.envoyer_message(client_socket, msg_fin)
                    break

                else:
                    print(f"[CLIENT {adresse}] Message inconnu: {type_msg}")

            except Exception as e:
                print(f"[CLIENT {adresse}] Erreur dans la boucle de jeu: {e}")
                break

    def jouer_tour_serveur(self, client_socket, partie, adresse):
        """
        Le serveur joue son tour (tir aléatoire intelligent).

        Args:
            client_socket: Socket du client
            partie: Instance de la partie
            adresse: Adresse du client
        """

        # Trouver une case non encore tirée
        tentatives = 0
        max_tentatives = 100
        x, y = -1, -1

        while tentatives < max_tentatives:
            x = random.randint(0, Protocole.TAILLE_GRILLE - 1)
            y = random.randint(0, Protocole.TAILLE_GRILLE - 1)

            # Vérifier si la case n'a pas déjà été tirée
            if partie.joueur2.grille_suivi[y][x] == Protocole.CASE_EAU:
                break

            tentatives += 1

        print(f"[SERVEUR] Tir en ({x}, {y})")

        # Traiter le tir du serveur
        resultat, bateau_coule, partie_terminee = partie.traiter_tir(x, y)

        # Envoyer le tir du serveur au client
        msg_tir = Message.creer_tir(x, y)
        self.envoyer_message(client_socket, msg_tir)

        # Envoyer le résultat
        msg_reponse = Message.creer_reponse_tir(resultat, x, y, bateau_coule)
        self.envoyer_message(client_socket, msg_reponse)

        print(f"[SERVEUR] Résultat: {resultat}")

        # Vérifier si la partie est terminée
        if partie_terminee:
            msg_fin = Message.creer_fin_partie(
                partie.obtenir_gagnant(),
                f"Partie terminée! Gagnant: {partie.obtenir_gagnant()}"
            )
            self.envoyer_message(client_socket, msg_fin)
            print(f"[CLIENT {adresse}] Partie terminée")

    def recevoir_message(self, client_socket):
        """
        Reçoit un message d'un client

        Args:
            client_socket: Socket du client

        Returns:
            Données reçues ou None en cas d'erreur
        """
        try:
            # Recevoir d'abord la taille du message (4 bytes)
            taille_data = client_socket.recv(4)
            if not taille_data:
                return None

            taille = int.from_bytes(taille_data, byteorder='big')

            # Recevoir le message complet
            data = b''
            while len(data) < taille:
                packet = client_socket.recv(taille - len(data))
                if not packet:
                    return None
                data += packet

            return data

        except Exception as e:
            print(f"[SERVEUR] Erreur de réception: {e}")
            return None

    def envoyer_message(self, client_socket, message):
        """
        Envoie un message à un client

        Args:
            client_socket: Socket du client
            message: Instance de Message à envoyer
        """
        try:
            data = message.serialiser()
            taille = len(data)

            # Envoyer d'abord la taille (4 bytes)
            client_socket.sendall(taille.to_bytes(4, byteorder='big'))

            # Envoyer le message
            client_socket.sendall(data)

        except Exception as e:
            print(f"[SERVEUR] Erreur d'envoi: {e}")

    def arreter(self):
        """Arrête le serveur"""
        print("[SERVEUR] Arrêt en cours...")
        self.actif = False

        if self.socket_serveur:
            try:
                self.socket_serveur.close()
            except Exception as e:
                print(f"[SERVEUR] Erreur de fermeture du socket: {e}")

        print("[SERVEUR] Arrêté")

"""


            # ========== ÉTAPE 2: RÉCEPTION DU PLACEMENT ==========
            print(f"[CLIENT {adresse}] En attente du placement des bateaux...")
            data = self.recevoir_message(client_socket)
            if not data:
                print(f"[CLIENT {adresse}] Pas de placement reçu")
                return

            msg_placement = Message.deserialiser(data)
            if msg_placement.type != Protocole.MSG_PLACEMENT_BATEAUX:
                print(f"[CLIENT {adresse}] Placement attendu, reçu: {msg_placement.type}")
                msg_erreur = Message.creer_erreur("Placement de bateaux attendu")
                self.envoyer_message(client_socket, msg_erreur)
                return

            positions = msg_placement.donnees.get("bateaux", [])
            print(f"[CLIENT {adresse}] Placement reçu: {len(positions)} bateaux")

            # ========== ÉTAPE 3: CRÉER LE JOUEUR CLIENT ==========
            joueur_client = Joueur(nom_client)

            # Placer les bateaux du client avec les positions reçues
            if not joueur_client.placer_bateaux_depuis_positions(positions):
                print(f"[CLIENT {adresse}] ✗ Placement invalide")
                msg_erreur = Message.creer_erreur("Placement de bateaux invalide")
                self.envoyer_message(client_socket, msg_erreur)
                return

            print(f"[CLIENT {adresse}] Bateaux du client placés avec succès")

            # Confirmer le placement
            msg_ok_placement = Message.creer_placement_ok()
            self.envoyer_message(client_socket, msg_ok_placement)

            # ========== ÉTAPE 4: CRÉER LA PARTIE ==========
            # Créer le joueur serveur avec placement aléatoire
            joueur_serveur = Joueur("Serveur")
            joueur_serveur.placer_bateaux_aleatoire()
            print(f"[CLIENT {adresse}] Bateaux du serveur placés")

            # Créer la partie
            partie = Partie(joueur_client, joueur_serveur)
            partie.etat = Protocole.ETAT_EN_COURS
            print(f"[CLIENT {adresse}] Partie créée et démarrée")

            # Envoyer le message de début de partie
            msg_debut = Message.creer_debut_partie()
            self.envoyer_message(client_socket, msg_debut)

            # ========== ÉTAPE 5: BOUCLE DE JEU ==========
            self.boucle_jeu(client_socket, partie, adresse)

"""