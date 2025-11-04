from reseau.protocole import Protocole
from base.joueur import Joueur

class Partie:
    def __init__(self, joueur1: Joueur, joueur2: Joueur=None):
        """
        Initialise une partie

        Args:
            joueur1: Premier joueur (client)
            joueur2: Deuxième joueur (serveur ou autre client)
        """
        self.joueur1 = joueur1
        self.joueur2 = joueur2 if joueur2 else Joueur("Serveur")
        self.etat = Protocole.ETAT_EN_ATTENTE
        self.tour_joueur1 = True  # True si c'est le tour du joueur1
        self.gagnant = None

    def demarrer(self):
        """Démarre la partie"""
        # S'assurer que les bateaux sont placés
        if not all(b.positionne for b in self.joueur1.bateaux):
            self.joueur1.placer_bateaux_aleatoire()

        if not all(b.positionne for b in self.joueur2.bateaux):
            self.joueur2.placer_bateaux_aleatoire()

        self.etat = Protocole.ETAT_EN_COURS

    def traiter_tir(self, x, y):
        """
        Traite un tir du joueur actif

        Args:
            x: Coordonnée x du tir
            y: Coordonnée y du tir

        Returns:
            Tuple (resultat, bateau_coule, partie_terminee)
        """
        if self.etat != Protocole.ETAT_EN_COURS:
            return None, None, False

        # Déterminer qui tire et qui reçoit
        if self.tour_joueur1:
            tireur = self.joueur1
            cible = self.joueur2
        else:
            tireur = self.joueur2
            cible = self.joueur1

        # Effectuer le tir
        resultat, bateau_coule = cible.recevoir_tir(x, y)

        # Enregistrer le tir dans la grille de suivi du tireur
        tireur.enregistrer_tir(x, y, resultat)

        # Vérifier si la partie est terminée
        if cible.tous_bateaux_coules():
            self.etat = Protocole.ETAT_TERMINEE
            self.gagnant = tireur.nom
            return resultat, bateau_coule, True

        # Changer de tour
        self.tour_joueur1 = not self.tour_joueur1

        return resultat, bateau_coule, False

    def abandonner(self, joueur_abandonne):
        """
        Gère l'abandon d'un joueur

        Args:
            joueur_abandonne: Nom du joueur qui abandonne
        """
        self.etat = Protocole.ETAT_ABANDONNEE
        if joueur_abandonne == self.joueur1.nom:
            self.gagnant = self.joueur2.nom
        else:
            self.gagnant = self.joueur1.nom

    def est_terminee(self):
        """Vérifie si la partie est terminée"""
        return self.etat in [Protocole.ETAT_TERMINEE, Protocole.ETAT_ABANDONNEE]

    def obtenir_gagnant(self):
        """Retourne le nom du gagnant"""
        return self.gagnant

    def obtenir_etat(self):
        """Retourne l'état actuel de la partie"""
        return self.etat

    def est_tour_joueur1(self):
        """Vérifie si c'est le tour du joueur 1"""
        return self.tour_joueur1

    def afficher_etat(self):
        """Affiche l'état complet de la partie (pour debug)"""
        print("\n" + "=" * 50)
        print(f"État de la partie: {self.etat}")
        print(f"Tour: {self.joueur1.nom if self.tour_joueur1 else self.joueur2.nom}")

        self.joueur1.afficher_grille(afficher_bateaux=True)
        self.joueur1.afficher_grille_suivi()
        self.joueur1.afficher_bateaux()

        print("\n" + "-" * 50)

        self.joueur2.afficher_grille(afficher_bateaux=True)
        self.joueur2.afficher_grille_suivi()
        self.joueur2.afficher_bateaux()

        print("=" * 50 + "\n")

    def __str__(self):
        return f"j1: {self.joueur1.nom} | j2: {self.joueur2.nom} | tour j1: {self.tour_joueur1} | etat: {self.etat}"