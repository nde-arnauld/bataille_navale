import threading
import uuid  # Pour générer un ID unique par partie

from commun import constantes as const
from commun.coeur_jeu.joueur import Joueur
from commun.coeur_jeu.partie import Partie


class GestionnairePartie:
    """
    Centralise le matchmaking PvP, la gestion des sessions de jeu actives, 
    et le relais des commandes entre joueurs.
    """
    
    def __init__(self):
        from serveur.reseau.gestionnaire_client import GestionnaireClient
        
        # {ID_PARTIE: Partie}
        self.parties_actives: dict[str, Partie] = {}

        # File d'attente pour le matchmaking [GestionnaireClient, ...]
        self.clients_en_attente: list[GestionnaireClient] = []

        # Verrou pour la manipulation de la file d'attente dans un contexte multi-thread
        self.lock_attente = threading.Lock()

        # Map pour trouver rapidement la partie ou l'adversaire d'un client
        # {Nom_joueur: ID_PARTIE}
        self.client_partie_map: dict[str, str] = {}

        # {game_id: {nom_joueur_1: bool, nom_joueur_2: bool}}
        # Pour s'assurer que les deux joueurs aient bien placé leurs navires
        self.etat_placement: dict[str, dict[str, bool]] = {}

    def mettre_en_attente(self, client: 'GestionnaireClient') -> None:
        """
        Ajoute un client à la file d'attente et tente de former un match.
        """
        with self.lock_attente:
            if len(self.clients_en_attente) >= 1:
                # Adversaire trouvé !
                adversaire = self.clients_en_attente.pop(0)

                # S'assurer que le client n'est pas déjà dans la map (cas de figure peu probable, mais sécurisant).
                if adversaire.nom_joueur in self.client_partie_map:
                    # Le client a peut-être été mis en attente deux fois ou à une session fantôme.
                    # On le renvoie en fin de liste (ou gère l'erreur).
                    self.clients_en_attente.append(client)
                    return

                print(f"[MATCHMAKING] Match trouvé: {adversaire.nom_joueur} vs {client.nom_joueur}")
                self.demarrer_partie_pvp(adversaire, client)
            else:
                # Ajouter à la file
                self.clients_en_attente.append(client)
                print(f"[MATCHMAKING] {client.nom_joueur} mis en attente.")

    def demarrer_partie_pvp(self, client1: 'GestionnaireClient', client2: 'GestionnaireClient') -> None:
        """
        Crée l'objet Partie, l'enregistre et notifie les deux clients.
        """

        # 1. Créer la partie
        # Les joueurs doivent être créés avec leur nom; les navires seront placés par le client
        joueur1 = Joueur(client1.nom_joueur)
        joueur2 = Joueur(client2.nom_joueur)

        nouvelle_partie = Partie(joueur1, joueur2)
        game_id = str(uuid.uuid4())

        self.etat_placement[game_id] = {
            client1.nom_joueur: False,
            client2.nom_joueur: False,
        }

        # 2. Enregistrer la partie et la map
        self.parties_actives[game_id] = nouvelle_partie
        self.client_partie_map[client1.nom_joueur] = game_id
        self.client_partie_map[client2.nom_joueur] = game_id

        # 3. Notifier les clients et leur assigner la partie
        # C'est ici que les GestionnairesClient vont recevoir leur objet Partie
        # Les clients sont retirés de la file d'attente (fait dans mettre_en_attente)

        # NOTE : Cette partie doit être gérée dans GestionnaireClient pour éviter
        # une dépendance bidirectionnelle trop forte. On passe l'information.

        # Les deux clients doivent maintenant passer à la phase de PLACEMENT

        # Mise à jour des clients avec les infos de la partie
        client1.partie_en_cours = nouvelle_partie
        client1.joueur_local = joueur1  # Le client gère Joueur1
        client2.partie_en_cours = nouvelle_partie
        client2.joueur_local = joueur2  # Le client gère Joueur2

        # Envoyer les messages d'adversaire trouvé et de début de partie
        client1.notifier_match_trouve(client2.nom_joueur)
        client2.notifier_match_trouve(client1.nom_joueur)

        print(f"[GestionnairePartie] Partie {game_id} lancée: {client1.nom_joueur} vs {client2.nom_joueur}. En attente de placement.")

        # Après le placement (géré par les clients), la partie sera formellement démarrée
        # et le premier tour sera notifié.


    def notifier_client_pret(self, client_pret: 'GestionnaireClient', client_actif_map: dict) -> None:
        """
        Marque un client comme prêt (navires placés) et vérifie si l'adversaire l'est aussi.
        Si les deux sont prêts, lance la partie et le premier tour.
        """
        game_id = self.client_partie_map.get(client_pret.nom_joueur)

        if not game_id or not (partie := self.parties_actives.get(game_id)):
            client_pret.notifier_erreur("Partie non trouvée ou inactive.")
            return

        # 1. Marquer le joueur actuel comme prêt
        with self.lock_attente:  # Verrouiller si la map est partagée/modifiée
            self.etat_placement[game_id][client_pret.nom_joueur] = True

            # 2. Vérifier l'état de l'adversaire
            etat_partie = self.etat_placement[game_id]

            # Trouver le nom de l'adversaire dans le dictionnaire d'état
            nom_adversaire = next(nom for nom in etat_partie if nom != client_pret.nom_joueur)

            # L'état est-il prêt pour les DEUX joueurs ?
            les_deux_sont_prets = all(etat_partie.values())

        if les_deux_sont_prets:
            # --- Lancement de la Partie PvP ---
            print(f"[GestionnairePartie] Les deux joueurs sont prêts. Démarrage du jeu.")

            # Récupérer l'instance de l'adversaire
            adversaire_client: 'GestionnaireClient' = self.trouver_gestionnaire_client(nom_adversaire, client_actif_map)

            if adversaire_client:
                # 3. Démarrer la partie métier
                partie.demarrer()

                # 4. Notifier le début de partie aux deux clients
                client_pret.notifier_debut_partie(adversaire_client.nom_joueur, const.MODE_VS_JOUEUR)
                adversaire_client.notifier_debut_partie(client_pret.nom_joueur, const.MODE_VS_JOUEUR)

                # 5. Lancer le premier tour
                GestionnairePartie.lancer_tour(partie, client_pret, adversaire_client)

            else:
                # Nettoyage si l'adversaire est parti
                self.retirer_partie(client_pret.nom_joueur)  # Cela retire aussi la partie et l'autre joueur
                client_pret.notifier_erreur("Adversaire déconnecté après placement. Fin de partie.")

    @staticmethod
    def lancer_tour(partie: Partie, client1: 'GestionnaireClient', client2: 'GestionnaireClient'):
        """ Détermine qui commence (J1 ou J2) et envoie le message de tour aux clients. """

        # Assurez-vous d'identifier qui est qui par rapport à l'objet 'Partie'.
        client_joueur1 = client1 if client1.joueur_local.nom == partie.joueur1.nom else client2
        client_joueur2 = client2 if client2.joueur_local.nom == partie.joueur2.nom else client1

        if partie.est_tour_joueur1:
            client_joueur1.notifier_tour(True)
            client_joueur2.notifier_tour(False)
        else:
            client_joueur1.notifier_tour(False)
            client_joueur2.notifier_tour(True)


    @staticmethod
    def trouver_gestionnaire_client(nom_joueur: str, clients_actifs_map: dict) -> 'GestionnaireClient|None':
        """
        Résout le nom du joueur en son GestionnaireClient actif,
        en utilisant la map fournie par l'EcouteurServeur.
        """
        return clients_actifs_map.get(nom_joueur)

    def trouver_adversaire(self, nom_joueur: str, clients_actifs_map: dict) -> 'GestionnaireClient|None':
        """
        Trouve le GestionnaireClient adversaire dans une partie active.
        (Nécessite la map fournie par l'EcouteurServeur pour trouver l'instance de l'adversaire.)
        """
        game_id = self.client_partie_map.get(nom_joueur)
        if not game_id:
            return None

        partie = self.parties_actives.get(game_id)
        if not partie:
            return None

        # Déterminer le nom de l'adversaire
        nom_adversaire = partie.joueur2.nom if partie.joueur1.nom == nom_joueur else partie.joueur1.nom

        # Utiliser la méthode mise à jour
        return GestionnairePartie.trouver_gestionnaire_client(nom_adversaire, clients_actifs_map)

    def traiter_tir(self, tireur_client: 'GestionnaireClient', clients_actifs_map: dict, x: int, y: int) -> tuple[str, str | None, bool]|None:
        """
        Relais et traite un tir du client sur la partie active.
        """
        game_id = self.client_partie_map.get(tireur_client.nom_joueur)
        if not game_id:
            return const.MSG_ERREUR, "Partie non trouvée", False

        partie = self.parties_actives[game_id]

        # 1. Vérification du tour (logique dans Partie.traiter_tir)
        if (partie.est_tour_joueur1 and tireur_client.nom_joueur == partie.joueur1.nom) or \
                (not partie.est_tour_joueur1 and tireur_client.nom_joueur == partie.joueur2.nom):

            # 2. Traitement du tir par la couche métier
            resultat, navire_coule, partie_terminee = partie.traiter_tir(x, y)

            # 3. Trouver le GestionnaireClient de l'adversaire
            nom_adversaire = partie.joueur2.nom if tireur_client.nom_joueur == partie.joueur1.nom else partie.joueur1.nom
            adversaire_client = GestionnairePartie.trouver_gestionnaire_client(nom_adversaire, clients_actifs_map)
            print(f"[GESTIONNAIRE PARTIE]: adversaire = {adversaire_client.nom_joueur}")
            # 4. Déléguer l'envoi de la notification au GestionnaireClient tireur et à son adversaire

            # Le tireur reçoit le résultat
            tireur_client.notifier_resultat_tir(x, y, resultat, navire_coule)

            # L'adversaire est notifié du coup
            if adversaire_client:
                adversaire_client.notifier_tir_recu(x, y, resultat, tireur_client.nom_joueur, navire_coule)

                # Gérer le changement de tour
                if not partie_terminee:
                    if resultat != const.TIR_DEJA_TIRE:
                        try:
                            tireur_client.notifier_tour(False)  # Tour de l'adversaire
                            adversaire_client.notifier_tour(True)  # C'est mon tour
                        except Exception as e:
                            print(f"[ERREUR CRITIQUE (GestionnairePartie)] lors de la bascule de tour : {e}")
                else:
                    client_vainqueur = tireur_client
                    client_perdant = adversaire_client

                    self.terminer_partie_pvp(client_vainqueur, client_perdant, partie)
                    return None

            return resultat, navire_coule, partie_terminee
        else:
            return const.MSG_ERREUR, "Ce n'est pas votre tour", False

    def terminer_partie_pvp(self, vainqueur: 'GestionnaireClient', perdant: 'GestionnaireClient', partie: Partie) -> None:
        """
        Termine formellement une partie PvP en notifiant les deux joueurs
        et en nettoyant les ressources serveur.
        """

        # 1. Envoyer le signal de victoire au vainqueur
        print(f"[GestionnairePartie] {vainqueur.nom_joueur} gagne la partie contre {perdant.nom_joueur}.")
        vainqueur.notifier_fin_partie("VICTOIRE", f"Félicitations {vainqueur.nom_joueur}, vous avez coulé tous les navires de votre adversaire {perdant.nom_joueur} !")

        # 2. Envoyer le signal de défaite au perdant
        perdant.notifier_fin_partie("DEFAITE", f"Dommage, vous avez perdu contre {vainqueur.nom_joueur}.")

        # 3. Nettoyer les ressources serveur
        # Ceci retire la partie de parties_actives et client_partie_map pour les deux joueurs.
        self.retirer_partie(vainqueur.nom_joueur)

    def transmettre_chat(self, envoyeur_client: 'GestionnaireClient', message: str, clients_actifs_map: dict) -> None:
        """
        Relais un message de chat à l'adversaire.
        (Nécessite la map des clients actifs.)
        """
        # 1. Trouver l'adversaire
        adversaire_client = self.trouver_adversaire(envoyeur_client.nom_joueur, clients_actifs_map)

        if adversaire_client:
            # 2. Le GestionnaireClient adverse envoie le message directement sur son socket
            adversaire_client.envoyer_chat(envoyeur_client.nom_joueur, message)

    def retirer_partie(self, nom_joueur: str) -> None:
        """
        Retire la partie de la structure après une fin (victoire/abandon).
        """
        game_id = self.client_partie_map.pop(nom_joueur, None)
        if game_id:
            # On vérifie si l'autre joueur est encore dans la map pour éviter la double suppression
            for joueur_nom, _id in list(self.client_partie_map.items()):
                if _id == game_id:
                    del self.client_partie_map[joueur_nom]
                    break

            if game_id in self.parties_actives:
                del self.parties_actives[game_id]
                print(f"[PARTIE] Partie {game_id} retirée.")