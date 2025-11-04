import socket
from .protocole import Protocole
from .message import Message
from base.joueur import Joueur

class Client:
    def __init__(self, host='127.0.0.1', port=5555):
        """
        Initialise le client

        Args:
            host: Adresse du serveur
            port: Port du serveur
        """
        self.host = host
        self.port = port
        self.socket_client = None
        self.connecte = False
        self.joueur = None
        self.en_partie = False
        self.tour_client = True

    def se_connecter(self, nom_joueur: str, placement_auto: bool = False, mode: str = Protocole.MODE_VS_SERVEUR):
        """
        Se connecte au serveur et envoie les positions des bateaux

        Args:
            nom_joueur: Nom du joueur
            placement_auto: Si True, placement automatique. Si False, placement manuel
            mode: MODE_VS_SERVEUR ou MODE_VS_JOUEUR

        Returns:
            True si la connexion a réussi, False sinon
        """
        try:
            # CRÉER LE SOCKET CLIENT
            self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_client.connect((self.host, self.port))

            print(f"[CLIENT] Connexion au serveur {self.host}:{self.port}")

            # CRÉER LE JOUEUR LOCAL
            self.joueur = Joueur(nom_joueur)

            # ENVOYER LE MESSAGE DE CONNEXION
            msg_connexion = Message.creer_connexion(nom_joueur)
            self.envoyer_message(msg_connexion)

            # ATTENDRE LA CONFIRMATION DE CONNEXION
            data = self.recevoir_message()
            if not data:
                print("[CLIENT] Erreur: Pas de réponse du serveur")
                return False

            msg_reponse = Message.deserialiser(data)
            if msg_reponse.type != Protocole.MSG_CONNEXION_OK:
                print(f"[CLIENT] Erreur: Réponse inattendue {msg_reponse.type}")
                return False

            print(f"[CLIENT] {msg_reponse.donnees.get('message', 'Connecté!')}")

            # ENVOYER LE CHOIX DU MODE
            msg_mode = Message.creer_choix_mode(mode)
            self.envoyer_message(msg_mode)

            # PLACEMENT DES BATEAUX
            if placement_auto:
                print("\n[CLIENT] Placement automatique de vos bateaux...")
                self.joueur.placer_bateaux_aleatoire()
                print("[CLIENT] Bateaux placés automatiquement!")
            else:
                print("\n[CLIENT] Placement manuel de vos bateaux...")
                self.joueur.placement_manuel_interactif()
                print("[CLIENT] Tous vos bateaux sont placés!")

            # AFFICHER UN RÉSUMÉ
            self.joueur.afficher_bateaux()

            # OBTENIR LES POSITIONS DES BATEAUX
            positions = self.joueur.obtenir_positions_bateaux()

            # ENVOYER LES POSITIONS AU SERVEUR
            print("\n[CLIENT] Envoi des positions au serveur...")
            msg_placement = Message.creer_placement_bateaux(positions)
            self.envoyer_message(msg_placement)

            # ATTENDRE LA CONFIRMATION DU PLACEMENT
            data = self.recevoir_message()
            if not data:
                print("[CLIENT] Erreur: Pas de confirmation du placement")
                return False

            msg_confirm = Message.deserialiser(data)
            if msg_confirm.type == Protocole.MSG_PLACEMENT_OK:
                print("[CLIENT] Positions confirmées par le serveur")
                self.connecte = True

                # SI MODE PVP, ATTENDRE UN ADVERSAIRE
                if mode == Protocole.MODE_VS_JOUEUR:
                    print("[CLIENT] Mode PvP - Attente de notification...")
                    data = self.recevoir_message()
                    if not data:
                        print("[CLIENT] ERREUR: Pas de réponse après placement (mode PvP)")
                        return False

                    msg = Message.deserialiser(data)
                    if msg.type == Protocole.MSG_ATTENTE_ADVERSAIRE:
                        print("[CLIENT] En attente d'un adversaire...")
                        print("[CLIENT] (Le socket reste ouvert, attendez...)")

                        # ATTENDRE QU'UN ADVERSAIRE SOIT TROUVÉ
                        data = self.recevoir_message()
                        if not data:
                            print("[CLIENT] ERREUR: Connexion perdue pendant l'attente")
                            return False

                        msg = Message.deserialiser(data)

                    if msg.type == Protocole.MSG_ADVERSAIRE_TROUVE:
                        adversaire = msg.donnees.get("adversaire")
                        print(f"[CLIENT] Adversaire trouvé: {adversaire}")
                    else:
                        print(f"[CLIENT] ERREUR: Message inattendu: {msg.type}")
                        return False
                print("[CLIENT] Connexion établie, prêt à jouer")
                return True
            elif msg_confirm.type == Protocole.MSG_ERREUR:
                print(f"[CLIENT] Erreur serveur: {msg_confirm.donnees.get('message')}")
                return False
            else:
                print(f"[CLIENT] Réponse inattendue: {msg_confirm.type}")
                return False

        except Exception as e:
            print(f"[CLIENT] Erreur de connexion: {e}")
            import traceback
            traceback.print_exc()
            return False

    def jouer(self):
        """Lance la partie"""
        if not self.connecte:
            print("[CLIENT] Non connecté au serveur")
            return

        try:
            print("[CLIENT] En attente du début de partie...")

            # ATTENDRE LE MESSAGE DE DÉBUT DE PARTIE
            data = self.recevoir_message()
            if not data:
                return

            msg_debut = Message.deserialiser(data)
            if msg_debut.obtenir_type() == Protocole.MSG_DEBUT_PARTIE:
                print("\n[CLIENT] === PARTIE COMMENCÉE ===\n")
                self.en_partie = True

                # BOUCLE DE JEU
                self.boucle_jeu()

        except Exception as e:
            print(f"[CLIENT] Erreur pendant la partie: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.deconnecter()

    def boucle_jeu(self):
        """Boucle principale du jeu (VS Serveur et VS Joueur)"""
        while self.en_partie:
            try:
                # Attendre la notification de tour
                print("\n[CLIENT] En attente de notification...")
                data = self.recevoir_message()
                if not data:
                    print("[CLIENT] Connexion perdue")
                    break

                message = Message.deserialiser(data)
                print(f"[CLIENT] Reçu: {message.type}")

                # C'EST NOTRE TOUR
                if message.type == Protocole.MSG_VOTRE_TOUR:
                    print("\n" + "=" * 60)
                    print("        ⚡ VOTRE TOUR ⚡")
                    print("=" * 60)

                    self.afficher_grilles()

                    # DEMANDER LES COORDONNÉES DU TIR
                    x, y = self.demander_coordonnees()

                    if x == -1:  # Abandon
                        msg_abandon = Message.creer_abandon()
                        self.envoyer_message(msg_abandon)
                        print("[CLIENT] Vous avez abandonné la partie")
                        self.en_partie = False
                        break

                    # ENVOYER LE TIR
                    msg_tir = Message.creer_tir(x, y)
                    self.envoyer_message(msg_tir)

                    # ATTENDRE LA RÉPONSE
                    data = self.recevoir_message()
                    if not data:
                        break

                    msg_reponse = Message.deserialiser(data)
                    self.traiter_reponse_tir(msg_reponse, est_notre_tir=True)

                    # VÉRIFIER SI LA PARTIE EST TERMINÉE
                    if msg_reponse.type == Protocole.MSG_FIN_PARTIE:
                        self.traiter_fin_partie(msg_reponse)
                        self.en_partie = False
                        break

                # C'EST LE TOUR DE L'ADVERSAIRE
                elif message.type == Protocole.MSG_TOUR_ADVERSAIRE:
                    print("\n" + "=" * 60)
                    print("\tTOUR DE L'ADVERSAIRE ")
                    print("=" * 60)
                    print("En attente du tir adverse...")

                    # ATTENDRE LE RÉSULTAT DU TIR ADVERSE
                    data = self.recevoir_message()
                    if not data:
                        break

                    msg_reponse = Message.deserialiser(data)
                    self.traiter_reponse_tir(msg_reponse, est_notre_tir=False)

                    # VÉRIFIER SI LA PARTIE EST TERMINÉE
                    if msg_reponse.type == Protocole.MSG_FIN_PARTIE:
                        self.traiter_fin_partie(msg_reponse)
                        self.en_partie = False
                        break

                # FIN DE PARTIE
                elif message.type == Protocole.MSG_FIN_PARTIE:
                    self.traiter_fin_partie(message)
                    self.en_partie = False
                    break

                # MODE VS SERVEUR
                elif message.type == Protocole.MSG_TIR:
                    # TIR DU SERVEUR EN MODE VS SERVEUR
                    data = self.recevoir_message()
                    if not data:
                        break

                    msg_resultat = Message.deserialiser(data)
                    self.traiter_reponse_tir(msg_resultat, est_notre_tir=False)

                    if msg_resultat.type == Protocole.MSG_FIN_PARTIE:
                        self.traiter_fin_partie(msg_resultat)
                        self.en_partie = False
                        break

                else:
                    print(f"[CLIENT] Message inattendu: {message.type}")

            except Exception as e:
                print(f"[CLIENT] Erreur dans la boucle de jeu: {e}")
                import traceback
                traceback.print_exc()
                break

    def traiter_reponse_tir(self, message, est_notre_tir):
        """Traite la réponse à un tir"""
        if message.type != Protocole.MSG_REPONSE_TIR:
            return

        x = message.donnees["x"]
        y = message.donnees["y"]
        resultat = message.donnees["resultat"]
        bateau_coule = message.donnees.get("bateau_coule")

        if est_notre_tir:
            print(f"\nVotre tir en ({x}, {y}): {resultat}")
            if bateau_coule:
                print(f"\tVous avez coulé le {bateau_coule} adverse!")

            # Mettre à jour notre grille de suivi
            self.joueur.enregistrer_tir(x, y, resultat)
        else:
            print(f"\nTir adverse en ({x}, {y}): {resultat}")
            if bateau_coule:
                print(f"\tVotre {bateau_coule} a été coulé!")

            # METTRE À JOUR NOTRE GRILLE
            self.joueur.recevoir_tir(x, y)

        input("\nAppuyez sur Entrée pour continuer...")

    def traiter_fin_partie(self, message):
        """Traite la fin de partie"""
        gagnant = message.donnees.get("gagnant")
        msg = message.donnees.get("message")

        print("\n" + "=" * 60)
        print("\tFIN DE LA PARTIE")
        print("=" * 60)
        print(msg)

        if gagnant == self.joueur.nom:
            print("\n\tVICTOIRE!")
        else:
            print("\n\tDÉFAITE")

        print("=" * 60)

        self.afficher_grilles()

    def boucle_jeu_2(self):
        while self.en_partie:
            try:
                print("\n[CLIENT] En attente de notification...")
                if self.tour_client:
                    # TOUR DU CLIENT
                    self.afficher_grilles()

                    # DEMANDER LES COORDONNÉES DU TIR
                    print("\n=== VOTRE TOUR ===")
                    x, y = self.demander_coordonnees()

                    if x == -1:  # Abandon
                        msg_abandon = Message.creer_abandon()
                        self.envoyer_message(msg_abandon)
                        print("[CLIENT] Vous avez abandonné la partie")
                        self.en_partie = False
                        break

                    # ENVOYER LE TIR
                    msg_tir = Message.creer_tir(x, y)
                    self.envoyer_message(msg_tir)

                    # ATTENDRE LA RÉPONSE
                    data = self.recevoir_message()
                    if not data:
                        break

                    msg_reponse = Message.deserialiser(data)
                    self.traiter_reponse(msg_reponse)

                    # VÉRIFIER SI LA PARTIE EST TERMINÉE
                    if msg_reponse.obtenir_type() == Protocole.MSG_FIN_PARTIE:
                        self.en_partie = False
                        break

                    # SI RATÉ, C'EST LE TOUR DU SERVEUR
                    if msg_reponse.obtenir_donnee("resultat") == Protocole.TIR_RATE:
                        self.tour_client = False

                else:
                    # TOUR DU SERVEUR
                    print("\n=== TOUR DU SERVEUR ===")
                    print("En attente du tir du serveur...")

                    # RECEVOIR LE TIR DU SERVEUR
                    data = self.recevoir_message()
                    if not data:
                        break

                    msg_tir_serveur = Message.deserialiser(data)

                    if msg_tir_serveur.obtenir_type() == Protocole.MSG_TIR:
                        x = msg_tir_serveur.obtenir_donnee("x")
                        y = msg_tir_serveur.obtenir_donnee("y")

                        # RECEVOIR LE RÉSULTAT
                        data = self.recevoir_message()
                        if not data:
                            break

                        msg_resultat = Message.deserialiser(data)
                        resultat = msg_resultat.obtenir_donnee("resultat")
                        bateau_coule = msg_resultat.obtenir_donnee("bateau_coule")

                        # AFFICHER LE RÉSULTAT
                        print(f"Serveur tire en ({x}, {y}): {resultat}")
                        if bateau_coule:
                            print(f"Votre {bateau_coule} a été coulé!")

                        # METTRE À JOUR LA GRILLE DU JOUEUR
                        self.joueur.recevoir_tir(x, y)

                        # VÉRIFIER SI LA PARTIE EST TERMINÉE
                        if msg_resultat.obtenir_type() == Protocole.MSG_FIN_PARTIE:
                            self.en_partie = False
                            break

                        # SI RATÉ, RETOUR AU TOUR DU CLIENT
                        if resultat == Protocole.TIR_RATE:
                            self.tour_client = True

                        input("\nAppuyez sur Entrée pour continuer...")

            except Exception as e:
                print(f"[CLIENT] Erreur dans la boucle de jeu: {e}")
                break

    def traiter_reponse(self, message):
        """
        Traite la réponse du serveur à un tir

        Args:
            message: Message reçu du serveur
        """
        type_msg = message.obtenir_type()

        if type_msg == Protocole.MSG_REPONSE_TIR:
            x = message.obtenir_donnee("x")
            y = message.obtenir_donnee("y")
            resultat = message.obtenir_donnee("resultat")
            bateau_coule = message.obtenir_donnee("bateau_coule")

            # ENREGISTRER LE RÉSULTAT SUR LA GRILLE DE SUIVI
            self.joueur.enregistrer_tir(x, y, resultat)

            # AFFICHER LE RÉSULTAT
            print(f"\nRésultat: {resultat}")
            if bateau_coule:
                print(f"Vous avez coulé le {bateau_coule} adverse!")

            input("\nAppuyez sur Entrée pour continuer...")

        elif type_msg == Protocole.MSG_FIN_PARTIE:
            gagnant = message.obtenir_donnee("gagnant")
            msg = message.obtenir_donnee("message")

            print("\n" + "=" * 50)
            print("=== FIN DE LA PARTIE ===")
            print(msg)

            if gagnant == self.joueur.nom:
                print("\tVICTOIRE!")
            else:
                print("\tDÉFAITE!")

            print("=" * 50)

            self.afficher_grilles()

    def demander_coordonnees(self):
        """
        Demande les coordonnées d'un tir à l'utilisateur

        Returns:
            Tuple (x, y) ou (-1, -1) pour abandonner
        """
        while True:
            try:
                entree = input("\nEntrez les coordonnées (ex: 3,5) ou 'abandon' pour quitter: ")

                if entree.lower() == 'abandon':
                    return -1, -1

                x, y = map(int, entree.split(','))

                if not Protocole.valider_coordonnees(x, y):
                    print(f"Coordonnées invalides! Utilisez des valeurs entre 0 et {Protocole.TAILLE_GRILLE - 1}")
                    continue

                # VÉRIFIER SI LA CASE A DÉJÀ ÉTÉ TIRÉE
                if self.joueur.grille_suivi[y][x] != Protocole.CASE_EAU:
                    print("Vous avez déjà tiré sur cette case!")
                    continue

                return x, y

            except ValueError:
                print("Format invalide! Utilisez le format: x,y (ex: 3,5)")
            except Exception as e:
                print(f"Erreur: {e}")

    def afficher_grilles(self):
        """Affiche les grilles du joueur"""
        print("\n" + "=" * 80)

        # Afficher les deux grilles côte à côte
        print("        VOS BATEAUX                          VOS TIRS")
        print("   ", end="")
        for i in range(Protocole.TAILLE_GRILLE):
            print(f" {i} ", end="")
        print("         ", end="")
        for i in range(Protocole.TAILLE_GRILLE):
            print(f" {i} ", end="")
        print()

        for y in range(Protocole.TAILLE_GRILLE):
            # Grille des bateaux
            print(f" {y} ", end="")
            for x in range(Protocole.TAILLE_GRILLE):
                case = self.joueur.grille[y][x]
                if case == Protocole.CASE_EAU:
                    print(" ~ ", end="")
                elif case == Protocole.CASE_BATEAU:
                    print(" B ", end="")
                elif case == Protocole.CASE_TOUCHE:
                    print(" X ", end="")
                elif case == Protocole.CASE_RATE:
                    print(" O ", end="")

            print("      ", end="")

            # GRILLE DE SUIVI
            print(f" {y} ", end="")
            for x in range(Protocole.TAILLE_GRILLE):
                case = self.joueur.grille_suivi[y][x]
                if case == Protocole.CASE_EAU:
                    print(" ~ ", end="")
                elif case == Protocole.CASE_TOUCHE:
                    print(" X ", end="")
                elif case == Protocole.CASE_RATE:
                    print(" O ", end="")
            print()

        print("=" * 80)

        # AFFICHER L'ÉTAT DES BATEAUX
        self.joueur.afficher_bateaux()

    def recevoir_message(self):
        """
        Reçoit un message du serveur

        Returns:
            Données reçues ou None en cas d'erreur
        """
        try:
            # RECEVOIR LA TAILLE DU MESSAGE
            taille_data = self.socket_client.recv(4)
            if not taille_data:
                return None

            taille = int.from_bytes(taille_data, byteorder='big')

            # RECEVOIR LE MESSAGE COMPLET
            data = b''
            while len(data) < taille:
                packet = self.socket_client.recv(taille - len(data))
                if not packet:
                    return None
                data += packet

            return data

        except Exception as e:
            print(f"[CLIENT] Erreur de réception: {e}")
            return None

    def envoyer_message(self, message):
        """
        Envoie un message au serveur

        Args:
            message: Instance de Message à envoyer
        """
        try:
            data = message.serialiser()
            taille = len(data)

            # ENVOYER LA TAILLE
            self.socket_client.sendall(taille.to_bytes(4, byteorder='big'))

            # ENVOYER LE MESSAGE
            self.socket_client.sendall(data)

        except Exception as e:
            print(f"[CLIENT] Erreur d'envoi: {e}")

    def deconnecter(self):
        """Déconnecte le client du serveur"""
        print("[CLIENT] Déconnexion...")

        if self.socket_client:
            try:
                self.socket_client.close()
            except Exception as e:
                print(f"[CLIENT] Erreur de fermeture de la socket cliente: {e}")

        self.connecte = False
        print("[CLIENT] Déconnecté")
