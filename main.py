from base.partie import Partie
from base.bateau import Bateau
from base.joueur import Joueur

if __name__ == "__main__":
    print("=== Bataille Navale Locale ===")

    # Création des joueurs
    j1 = Joueur(input("Nom du joueur 1 : "))
    j2 = Joueur(input("Nom du joueur 2 : "))

    # Liste de bateaux à placer
    # flotte = [("Porte-avions", 4), ("Croiseur", 3), ("Sous-marin", 2)]
    flotte = [("Porte-avions", 4)]

    # Placement manuel pour chaque joueur
    for joueur in [j1, j2]:
        print(f"\n--- Placement des bateaux pour {joueur.nom} ---")
        joueur.afficher_grille()
        for nom, taille in flotte:
            while True:
                try:
                    print(f"\nPlacer le {nom} (taille {taille})")
                    x = int(input("Ligne de départ (0-9) : "))
                    y = int(input("Colonne de départ (0-9) : "))

                    orientation = input("Orientation (H/V) : ").upper()
                    
                    while orientation != "H" and orientation != "V":
                        orientation = input("Orientation (H/V) : ").upper()

                    bateau = Bateau(nom, taille, orientation)

                    joueur.placer_bateau(bateau, (x, y))
                    joueur.afficher_grille()
                    break
                except Exception as e:
                    print(f"Erreur : {e}. Réessaie.")

    # Démarrage de la partie
    partie = Partie(j1, j2)

    while partie.en_cours:
        joueur = partie.tour_actuel
        print(f"\n--- Tour de {joueur.nom} ---")

        # Afficher la grille adverse publique
        adversaire = partie.joueur2 if joueur == partie.joueur1 else partie.joueur1
        adversaire.afficher_grille_publique()

        try:
            x = int(input("Ligne de tir (0-9) : "))
            y = int(input("Colonne de tir (0-9) : "))
            partie.tirer((x, y))
        except Exception as e:
            print(f"Erreur de tir : {e}")

        # Afficher les grilles à chaque tour
        joueur.afficher_grille_publique()
        adversaire.afficher_grille_publique()
