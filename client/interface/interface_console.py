import sys
import os
import time

from typing import Any
from commun import constantes as const
from commun.reseau.message import Message
from commun.coeur_jeu.joueur import Joueur
from client.reseau.connecteur_client import ConnecteurClient

# --- NOUVELLES CONSTANTES D'ÉTAT LOCAL (pour la clarté) ---
# Nécessaires ici, car elles ne sont pas dans les constantes.py
ETAT_LOCAL_DECONNECTE = "DECONNECTE"
ETAT_LOCAL_CHOIX_MODE = "CHOIX_MODE"
ETAT_LOCAL_PLACEMENT = "PLACEMENT"
ETAT_LOCAL_JEU = "JEU_EN_COURS"
ETAT_LOCAL_ATTENTE = "ATTENTE_ADVERSAIRE"
ETAT_LOCAL_REPRISE = "CHOIX_REPRISE"


class InterfaceConsole:
    """
    Gère l'interface utilisateur (menus, affichage, saisie) et le flux de jeu côté client.
    Agit comme le contrôleur en envoyant des commandes au ConnecteurClient.
    """

    def __init__(self, host_serveur: str | None):
        self.host_serveur = host_serveur
        self.connecteur: ConnecteurClient | None = None
        self.joueur_local: Joueur | None = None
        self.adversaire_nom: str | None = None
        self.statut_connexion: str = const.STATUS_HORS_LIGNE  
        self.mode_jeu: str | None = None
        self.etat_actuel: str = ETAT_LOCAL_DECONNECTE
        self.est_mon_tour: bool = False
        self.partie_sauvegardee_existe: bool = False

    def lancer(self):
        """ Point d'entrée principal de l'application client. """
        while True:
            # InterfaceConsole.nettoyer_console()
            print("=" * 40)
            print("  CONFIGURATION DU SERVEUR")
            print("=" * 40)

            # Demander l'adresse IP
            host = input(f"Veuillez saisir l'adresse IP du serveur (ex: 127.0.0.1) ou '{const.CMD_QUITTER.lower()}': ").strip()

            if host.upper() == const.CMD_QUITTER:  
                print("Arrêt du client.")
                sys.exit(0)

            if host:
                self.host_serveur = host
                break
            else:
                print("Adresse IP invalide ou vide. Réessayez.")
                time.sleep(1)

        self.menu_principal()

    # --- 1. Gestion du Flux et Menus ---

    def menu_principal(self):
        """ Affiche le menu d'authentification et gère les choix Initiaux. """
        while True:
            # InterfaceConsole.nettoyer_console()
            print("=" * 40)
            print("  BATAILLE NAVALE - CLIENT CONSOLE")
            print("=" * 40)
            print(f"{const.CHOIX_MENU_CONNEXION}. Connexion (Login)")
            print(f"{const.CHOIX_MENU_INSCRIPTION}. Inscription (Register)")
            print(f"{const.CHOIX_MENU_QUITTER}. Quitter")
            print("-" * 40)

            choix = input(f"Votre choix ({const.CHOIX_MENU_CONNEXION}-{const.CHOIX_MENU_QUITTER}): ").strip()

            if choix == const.CHOIX_MENU_QUITTER:  
                print("Arrêt du client.")
                sys.exit(0)

            elif choix == const.CHOIX_MENU_CONNEXION:  
                self._demarrer_session(const.MSG_AUTH_LOGIN)

            elif choix == const.CHOIX_MENU_INSCRIPTION:  
                self._demarrer_session(const.MSG_AUTH_REGISTER)

            else:
                print("Choix invalide. Réessayez.")

            if self.connecteur and self.connecteur.tcp_connecte:
                self.main_loop()

    def _demarrer_session(self, mode_auth: str):
        """ Gère la phase d'authentification UDP et de connexion TCP. """
        nom = input("Nom d'utilisateur: ").strip()
        mdp = input("Mot de passe: ").strip()

        self.connecteur = ConnecteurClient(self.host_serveur)
        self.connecteur.set_callback_traitement(self.traiter_message_serveur)

        # 1. Authentification UDP
        succes, msg, host_tcp, port_tcp, statut_partie = self.connecteur.authentification_udp(nom, mdp, mode_auth)

        print(f"\n[AUTH] Réponse: {msg}")

        if not succes:
            input("Appuyez sur Entrée pour continuer...")
            return

        self.partie_sauvegardee_existe = (statut_partie == const.MSG_PARTIE_SAUVEGARDEE_EXISTE)

        # 2. Connexion TCP
        if not self.connecteur.connecter_tcp(host_tcp, port_tcp):
            print("[CONNEXION] Échec de la connexion au serveur de jeu TCP.")
            input("Appuyez sur Entrée pour revenir au menu...")
            return

        self.statut_connexion = const.STATUS_CONNECTE  
        print("[CONNEXION] Connexion au serveur de jeu réussie.")

    def main_loop(self):
        """ La boucle principale de jeu après la connexion. """

        while self.joueur_local is None and self.connecteur.actif:
            time.sleep(0.1)

        if self.partie_sauvegardee_existe:
            self.etat_actuel = ETAT_LOCAL_REPRISE
            self._menu_reprise_partie()
        else:
            self.etat_actuel = ETAT_LOCAL_CHOIX_MODE
            self._menu_choix_mode()

        try:
            while self.connecteur.actif:
                # InterfaceConsole.nettoyer_console()

                if self.etat_actuel == ETAT_LOCAL_JEU:
                    self._afficher_jeu()
                    if self.est_mon_tour:
                        self.saisir_tir_ou_chat()
                    else:
                        self.saisir_chat()

                elif self.etat_actuel == ETAT_LOCAL_PLACEMENT:
                    pass

                elif self.etat_actuel == ETAT_LOCAL_ATTENTE:
                    self._afficher_jeu()
                    print(
                        f"\n[JEU] En attente d'un adversaire... Tapez '{const.CMD_ABANDONNER}' pour annuler l'attente.")
                    self.saisir_chat()

                time.sleep(0.1)
        except Exception as e:
            print(f"Erreur dans la boucle principale: {e}")
        finally:
            self.connecteur.deconnecter()

    # --- 2. Menus de Configuration ---

    def _menu_reprise_partie(self):
        """ Demande au joueur s'il veut reprendre la partie sauvegardée. """
        while self.etat_actuel == ETAT_LOCAL_REPRISE:
            # InterfaceConsole.nettoyer_console()
            print("=" * 40)
            print("  PARTIE SAUVEGARDÉE TROUVÉE")
            print("=" * 40)
            print(f"{const.CHOIX_REPRENDRE_PARTIE}. Reprendre la partie (REPRENDRE_PARTIE)")
            print(f"{const.CHOIX_NOUVELLE_PARTIE}. Nouvelle partie (SUPPRIME la sauvegarde)")
            print("-" * 40)

            choix = input(f"Votre choix ({const.CHOIX_REPRENDRE_PARTIE}/{const.CHOIX_NOUVELLE_PARTIE}): ").strip()

            if choix == const.CHOIX_REPRENDRE_PARTIE:
                self.connecteur.envoyer_commande(Message(const.MSG_REPRENDRE_PARTIE))
                self.etat_actuel = ETAT_LOCAL_ATTENTE
                break
            elif choix == const.CHOIX_NOUVELLE_PARTIE:
                self.connecteur.envoyer_commande(Message(const.MSG_NOUVELLE_PARTIE))
                self.etat_actuel = ETAT_LOCAL_CHOIX_MODE
                break
            else:
                print("Choix invalide.")
                time.sleep(1)

    def _menu_choix_mode(self):
        """ Demande au joueur s'il veut jouer en Solo ou PvP. """
        while self.etat_actuel == ETAT_LOCAL_CHOIX_MODE:
            # InterfaceConsole.nettoyer_console()
            print("=" * 40)
            print("  CHOIX DU MODE DE JEU")
            print("=" * 40)
            print(
                f"{const.CHOIX_MODE_SOLO}. Jouer contre le Serveur ({const.MODE_VS_SERVEUR})")  # MODE_VS_SERVEUR est la constante métier.
            print(
                f"{const.CHOIX_MODE_PVP}. Jouer contre un autre Joueur ({const.MODE_VS_JOUEUR})")  # MODE_VS_JOUEUR est la constante métier.
            print("-" * 40)

            choix = input(f"Votre choix ({const.CHOIX_MODE_SOLO}/{const.CHOIX_MODE_PVP}): ").strip()

            if choix == const.CHOIX_MODE_SOLO:  
                self.mode_jeu = const.MODE_VS_SERVEUR
                self.connecteur.envoyer_commande(Message.creer_choix_mode(const.MODE_VS_SERVEUR))
                self.etat_actuel = ETAT_LOCAL_PLACEMENT # En attente de réponse, les messages reçus sont ignorés
                break
            elif choix == const.CHOIX_MODE_PVP:  
                self.mode_jeu = const.MODE_VS_JOUEUR
                self.connecteur.envoyer_commande(Message.creer_choix_mode(const.MODE_VS_JOUEUR))
                self.etat_actuel = ETAT_LOCAL_ATTENTE
                break
            else:
                print("Choix invalide.")
                time.sleep(1)

        if self.mode_jeu == const.MODE_VS_SERVEUR:
            self.gerer_placement_navires()

    # --- 3. Logique de Placement ---

    def gerer_placement_navires(self):
        """ Gère la boucle de placement (manuel ou aléatoire) et envoie au serveur. """

        self.etat_actuel = ETAT_LOCAL_PLACEMENT

        mode = InterfaceConsole._menu_choix_placement()

        if mode == const.CHOIX_PLACEMENT_MANUEL: 
            positions = self._placement_manuel_interactif()
        else:  # Aléatoire
            self.joueur_local.placer_navires_aleatoire()
            positions = self.joueur_local.obtenir_positions_navires()

        msg_placement = Message.creer_placement_navires(positions)
        self.connecteur.envoyer_commande(msg_placement)

        print("Positions envoyées, attente de la validation du serveur...")

    @staticmethod
    def _menu_choix_placement() -> str:
        """ Affiche le menu pour choisir le placement (manuel ou aléatoire). """
        while True:
            # InterfaceConsole.nettoyer_console()
            print("=" * 40)
            print("  MODE DE PLACEMENT")
            print("=" * 40)
            print(f"{const.CHOIX_PLACEMENT_MANUEL}. Placement manuel")
            print(f"{const.CHOIX_PLACEMENT_AUTO}. Placement automatique (aléatoire)")
            print("-" * 40)

            choix = input(f"Votre choix ({const.CHOIX_PLACEMENT_MANUEL}/{const.CHOIX_PLACEMENT_AUTO}): ").strip()
            if choix == const.CHOIX_PLACEMENT_MANUEL or choix == const.CHOIX_PLACEMENT_AUTO:
                return choix
            print("Choix invalide.")
            time.sleep(1)

    def _placement_manuel_interactif(self) -> list[dict[str, Any]]:
        """ Réalise le placement interactif de tous les navires en une seule ligne de saisie. """

        # Assurez-vous que Joueur(nom) initialise bien des navires non positionnés.
        if self.joueur_local is None:
            self.joueur_local = Joueur(self.connecteur.nom_joueur)

        navires_a_placer = self.joueur_local.navires

        print("\n=== PLACEMENT MANUEL DES NAVIRES ===\n")

        for navire in navires_a_placer:
            place = False
            while not place:
                self._afficher_jeu()
                print(f"\nPlacez: {navire.nom} ({navire.taille} cases)")

                try:
                    # 1. Position + Orientation
                    print(f"Format: colonne (0-{const.TAILLE_GRILLE - 1}), ligne (0-{const.TAILLE_GRILLE - 1}), orientation ({const.HORIZONTAL}/{const.VERTICAL})")
                    print("Exemple: 0, 2, V")
                    saisie = input(f"Entrez: ").strip()

                    # 2. Séparation et Nettoyage
                    parties = [p.strip() for p in saisie.split(',')]

                    if len(parties) != 3:
                        print("Format invalide. Veuillez saisir Ligne, Colonne, Orientation (ex: 5, 5, H).")
                        continue

                    # 3. Conversion et Validation
                    colonne = int(parties[0])
                    ligne = int(parties[1])
                    orientation = parties[2].upper()

                    # Validation des coordonnées
                    if not (0 <= ligne < const.TAILLE_GRILLE and 0 <= colonne < const.TAILLE_GRILLE):
                        print("Coordonnées hors limites (0-9).")
                        continue

                    # Validation de l'orientation
                    if orientation not in [const.HORIZONTAL, const.VERTICAL]:
                        print("Orientation invalide! Utilisez H ou V.")
                        continue

                    # Validation et placement
                    # Votre logique utilise (colonne, ligne) pour (x, y) dans Joueur/Navire
                    if self.joueur_local.placement_valide(navire, colonne, ligne, orientation):

                        # Mise à jour des objets Navire et Grille
                        navire.positionner(colonne, ligne, orientation)
                        self.joueur_local.placer_navire(navire, colonne, ligne, orientation)

                        print(f"{navire.nom} placé. Prochain navire.")
                        place = True
                    else:
                        print("Placement impossible (collision ou hors grille).")

                except ValueError:
                    print("Erreur de saisie! Assurez-vous que Ligne et Colonne sont des nombres entiers.")
                except Exception as e:
                    print(f"Erreur inattendue: {e}")

        # InterfaceConsole.nettoyer_console()
        self._afficher_jeu()
        print("\n=== PLACEMENT TERMINÉ ===")
        input("Appuyez sur Entrée pour continuer (envoi au serveur)...")

        # Utiliser la méthode réelle si le nom a été mis à jour dans Joueur
        return self.joueur_local.obtenir_positions_navires()

    # --- 4. Logique de Jeu (Tour et Chat) ---

    def saisir_tir_ou_chat(self):
        """ Demande la saisie pour un tir ou une commande spéciale. """
        saisie = input(f"\n[VOTRE TOUR] Tirez (ex: 5, 7) ou tapez '{const.CMD_CHAT.lower()}', "
                       f"'{const.CMD_SAUVEGARDER.lower()}', '{const.CMD_ABANDONNER.lower()}': ").strip().upper()

        if saisie == const.CMD_CHAT:
            msg = input("Votre message: ").strip()
            if msg:
                self.connecteur.envoyer_commande(Message.creer_chat(msg))

        elif saisie == const.CMD_SAUVEGARDER:
            self.connecteur.envoyer_commande(Message.creer_sauvegarder_partie())
            print("Demande de sauvegarde envoyée.")

        elif saisie == const.CMD_ABANDONNER:
            self.connecteur.envoyer_commande(Message.creer_abandon())
            self.connecteur.deconnecter()

        else:
            try:
                # 1. Tentative de séparation par virgule
                parties = [p.strip() for p in saisie.split(',')]

                # Vérifier si on a exactement deux parties (colonne et ligne)
                if len(parties) == 2:
                    colonne = int(parties[0])
                    ligne = int(parties[1])

                    # 2. Validation des limites de la grille
                    if 0 <= ligne < const.TAILLE_GRILLE and 0 <= colonne < const.TAILLE_GRILLE:
                        self.connecteur.envoyer_commande(Message.creer_tir(colonne, ligne))
                        self.est_mon_tour = False
                        print(f"Tir envoyé : ({colonne}, {ligne})")
                    else:
                        print(f"Coordonnées hors limites (0 à {const.TAILLE_GRILLE - 1}).")

                else:
                    # Si la saisie n'est ni une commande, ni le nouveau format (x, y).
                    print("Commande ou format de tir invalide. Utilisez 'colonne, ligne' (ex: 5, 7).")

            except ValueError:
                # Capturé si int() échoue (si l'utilisateur saisit "A, B")
                print("Format de tir invalide. Les coordonnées doivent être des nombres entiers (ex: 5, 7).")
            except Exception as e:
                print(f"Erreur inattendue lors de la saisie: {e}")

    def saisir_chat(self):
        """ Permet de chatter quand ce n'est pas le tour de jeu. """
        saisie = input(
            f"\n[TOUR ADVERSE] Saisissez '{const.CMD_CHAT.lower()}', '{const.CMD_SAUVEGARDER.lower()}', '{const.CMD_ABANDONNER.lower()}' ou attendez: ").strip().upper()

        if saisie == const.CMD_CHAT:  
            msg = input("Votre message: ").strip()
            if msg:
                self.connecteur.envoyer_commande(Message.creer_chat(msg))

        elif saisie == const.CMD_SAUVEGARDER:  
            self.connecteur.envoyer_commande(Message.creer_sauvegarder_partie())
            print("Demande de sauvegarde envoyée.")

        elif saisie == const.CMD_ABANDONNER:  
            self.connecteur.envoyer_commande(Message.creer_abandon())
            self.connecteur.deconnecter()

    # --- 5. Traitement des Messages du Serveur (Le Callback) ---

    def traiter_message_serveur(self, message: Message):
        """ 
        Gère tous les messages entrants du serveur.
        """

        # Gère la validation du placement
        if self.etat_actuel == ETAT_LOCAL_PLACEMENT:
            if message.type == const.MSG_PLACEMENT_OK:
                print("\n[SERVEUR] Placement validé. Attente du début de partie...")
                self.etat_actuel = ETAT_LOCAL_ATTENTE
                return
            elif message.type == const.MSG_ERREUR:
                print(f"\n[SERVEUR] Erreur de placement: {message.obtenir_donnee('message')}. Recommencez.")
                self.gerer_placement_navires()
                return

        # Gestion des autres messages
        if message.type == const.MSG_CONNEXION_OK:
            self.joueur_local = Joueur(self.connecteur.nom_joueur)

        elif message.type == const.MSG_PARTIE_REPRISE:
            joueur_data = message.obtenir_donnee("joueur_etat")
            est_mon_tour = message.obtenir_donnee("est_mon_tour", False)
            nom_adversaire = message.obtenir_donnee("nom_adversaire", const.NOM_SERVEUR)

            if joueur_data:
                self.joueur_local = Joueur.from_dict(joueur_data)
                self.est_mon_tour = est_mon_tour
                self.statut_connexion = const.STATUS_CONNECTE
                self.etat_actuel = ETAT_LOCAL_JEU
                print("\n[JEU] Partie sauvegardée chargée. Reprise du jeu.")

                # hum
                if nom_adversaire == const.NOM_SERVEUR:
                    print("Appuyez pour continuer ...")

        elif message.type == const.MSG_ATTENTE_ADVERSAIRE:
            print("\n[JEU] En attente d'un adversaire...")
            self.etat_actuel = ETAT_LOCAL_ATTENTE

        elif message.type == const.MSG_ADVERSAIRE_TROUVE:
            self.adversaire_nom = message.obtenir_donnee("adversaire")
            print(f"\n[JEU] Adversaire trouvé: {self.adversaire_nom}. Préparez le placement!")
            self.gerer_placement_navires()
            self.etat_actuel = ETAT_LOCAL_PLACEMENT

        elif message.type == const.MSG_DEBUT_PARTIE:
            print("\n[JEU] La partie commence!")
            self.etat_actuel = ETAT_LOCAL_JEU

        elif message.type == const.MSG_VOTRE_TOUR:
            self.est_mon_tour = True
            print("\n<<< C'EST VOTRE TOUR >>>")

        elif message.type == const.MSG_TOUR_ADVERSAIRE:
            self.est_mon_tour = False
            print("\n<<< Tour de l'adversaire >>>")

        elif message.type == const.MSG_REPONSE_TIR:
            resultat = message.obtenir_donnee("resultat")
            x = message.obtenir_donnee("x")
            y = message.obtenir_donnee("y")

            if not self.est_mon_tour:
                self.joueur_local.enregistrer_tir(x, y, resultat)
                print(f"\n[RÉSULTAT] Tir en ({x},{y}): {resultat}!")
                if resultat == const.TIR_COULE:
                    print(f"  -> Navire coulé: {message.obtenir_donnee('bateau_coule')}")

            else:  # Tir adverse reçu
                print(f"\n[ADVERSE] Tir reçu en ({x},{y}). Résultat: {resultat}!")

        elif message.type == const.MSG_REPONSE_TIR_RECU:
            resultat = message.obtenir_donnee("resultat")
            adversaire = message.obtenir_donnee("adversaire")
            x = message.obtenir_donnee("x")
            y = message.obtenir_donnee("y")

            if not self.est_mon_tour:
                self.joueur_local.recevoir_tir(x, y)
                print(f"\n[RÉSULTAT '{adversaire}'] Tir en ({x},{y}): {resultat}!")
                if resultat == const.TIR_COULE:
                    print(f"  -> Navire coulé: {message.obtenir_donnee('bateau_coule')}")

            else:  # Tir adverse reçu
                print(f"\n[ADVERSE] Tir reçu en ({x},{y}). Résultat: {resultat}!")

        elif message.type == const.MSG_CHAT_GLOBAL:
            envoyeur = message.obtenir_donnee("envoyeur")
            msg = message.obtenir_donnee("message")
            print(f"\n[CHAT - {envoyeur}] {msg}")

        elif message.type == const.MSG_FIN_PARTIE:
            gagnant = message.obtenir_donnee("gagnant")
            detail = message.obtenir_donnee("message")
            print(f"\n!!! FIN DE PARTIE !!!")
            print(f"GAGNANT: {gagnant}. Raison: {detail}")
            self.connecteur.deconnecter()

        elif message.type == const.MSG_ERREUR:
            print(f"\n[ERREUR SERVEUR] {message.obtenir_donnee('message')}")

    # --- 6. Affichage Console ---
    @staticmethod
    def nettoyer_console():
        """ Nettoie l'écran de la console (basique). """
        os.system('cls' if os.name == 'nt' else 'clear')

    def _afficher_jeu(self):
        """ Affiche l'état complet de la partie (grilles et statut). """
        # InterfaceConsole.nettoyer_console()

        if not self.joueur_local:
            return

        print("=" * 70)
        print(f"JEU ACTIF | Joueur: {self.joueur_local.nom} | Adversaire: {self.adversaire_nom or 'Attente...'}")
        print(
            f"Mode: {self.mode_jeu} | État: {self.etat_actuel} | Tour: {'VOUS' if self.est_mon_tour else 'Adversaire'}")
        print("-" * 70)

        # Affichage de la Grille Principale (Mes navires)
        print("\n--- MA GRILLE (Navires) ---")
        self.joueur_local.afficher_grille(afficher_navires=True)

        # Affichage de la Grille de Suivi (Mes tirs)
        print("\n--- GRILLE DE SUIVI (Tirs effectués) ---")
        self.joueur_local.afficher_grille_suivi()

        # Afficher l'état des navires
        self.joueur_local.afficher_navires()